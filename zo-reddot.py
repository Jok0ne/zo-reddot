#!/usr/bin/env python3
"""
zo-reddot — disable TrackPoint motion while keeping the buttons.

Exclusively grabs the kernel input device of a ThinkPad TrackPoint (or any
pointing-stick), creates a uinput device that only carries BTN_LEFT /
BTN_RIGHT / BTN_MIDDLE, and forwards button events. Relative motion
(EV_REL X/Y) is dropped entirely.

Why: on many modern ThinkPads (especially Elantech units like the Yoga 370),
the three TrackPoint buttons below the spacebar are wired to the TrackPoint
input device, NOT the touchpad. Disabling the TrackPoint via `inhibited=1`
therefore also kills the buttons. BIOS-level TrackPoint disable does the
same. libinput's pointing-stick sensitivity options either don't exist for
these devices or are ignored by libinput. This daemon solves that by
filtering events at the kernel/uinput layer.

Usage: started by systemd (see zo-reddot.service). Needs root for
exclusive grab + uinput creation. Set TRACKPOINT_NAME env var to override
device matching if your device is named differently than the Yoga-370
default.
"""
import os
import sys
import glob

from evdev import InputDevice, UInput, ecodes as e

DEFAULT_NAME = "ETPS/2 Elantech TrackPoint"
DEVICE_NAME = os.environ.get("TRACKPOINT_NAME", DEFAULT_NAME)


def find_device(name: str):
    """Return InputDevice whose .name matches exactly, or None."""
    for path in sorted(glob.glob("/dev/input/event*")):
        try:
            dev = InputDevice(path)
        except (OSError, PermissionError):
            continue
        if dev.name == name:
            return dev
    return None


def main() -> int:
    src = find_device(DEVICE_NAME)
    if src is None:
        print(
            f"zo-reddot: no input device named '{DEVICE_NAME}' found. "
            f"List devices with 'cat /proc/bus/input/devices' and override "
            f"via TRACKPOINT_NAME env var if needed.",
            file=sys.stderr,
        )
        return 1

    print(
        f"zo-reddot: grabbing {src.path} ({src.name})", file=sys.stderr
    )

    capabilities = {
        e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
    }
    ui = UInput(capabilities, name="TrackPoint Buttons Only", version=0x1)
    src.grab()
    print(
        "zo-reddot: grabbed + uinput up — buttons only, motion dropped",
        file=sys.stderr,
    )

    try:
        for event in src.read_loop():
            if event.type == e.EV_KEY and event.code in (
                e.BTN_LEFT,
                e.BTN_RIGHT,
                e.BTN_MIDDLE,
            ):
                ui.write_event(event)
                ui.syn()
            # All other event types (EV_REL X/Y, scroll emulation, SYN) are
            # dropped so that the TrackPoint itself has no effect on the
            # cursor while the buttons remain fully functional.
    except KeyboardInterrupt:
        pass
    finally:
        try:
            src.ungrab()
        except Exception:
            pass
        ui.close()
        print("zo-reddot: released + cleaned up", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
