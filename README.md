<p align="center">
  <img src="docs/header.jpg" alt="zo-reddot — disable ThinkPad TrackPoint motion, keep the buttons" width="100%">
</p>

<h1 align="center">zo-reddot — disable ThinkPad TrackPoint motion, keep the buttons on Linux</h1>

<h3 align="center">Dead pointer. Live buttons. Works on Wayland + X11. No BIOS toggle, no xinput gymnastics, no dotfile religion.</h3>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-ff2e2e?style=for-the-badge" alt="GPL-3.0 License"></a>
  <img src="https://img.shields.io/badge/platform-Linux-000000?style=for-the-badge&logo=linux&logoColor=white" alt="Linux">
  <img src="https://img.shields.io/badge/python-3.7%2B-000000?style=for-the-badge&logo=python&logoColor=ff2e2e" alt="Python 3.7+">
  <img src="https://img.shields.io/badge/display-Wayland%20%7C%20X11-ff2e2e?style=for-the-badge" alt="Wayland | X11">
  <img src="https://img.shields.io/badge/service-systemd-000000?style=for-the-badge" alt="systemd">
  <img src="https://img.shields.io/badge/status-stable-ff2e2e?style=for-the-badge" alt="stable">
</p>

<p align="center">
  <a href="#the-problem">Problem</a> ·
  <a href="#install">Install</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#configuration">Config</a> ·
  <a href="#hardware">Hardware</a> ·
  <a href="#troubleshooting">Troubleshooting</a> ·
  <a href="#design-notes">Design</a>
</p>

---

## The problem

On modern Linux ThinkPads — **Yoga 370, T470, X270, X1 Carbon Gen 5** and most of the 2017-onward Elantech-digitizer lineup — the three TrackPoint buttons below the spacebar share an input device with the red dot (pointing stick) itself. Disable the pointer (BIOS toggle, `inhibited=1`, `xinput disable`) and you lose the buttons too. On Wayland, the classic `Coordinate Transformation Matrix` escape hatch is gone.

Every forum answer, every Stack Overflow thread, every dotfile gist ignores this. Here's the receipt:

| Approach | Works? | Problem |
|---|---|---|
| `echo 1 > /sys/class/input/inputN/inhibited` | ✗ | Disables the whole device, buttons included |
| BIOS "TrackPoint = Disabled" | ✗ | Same — EC turns off the device entirely |
| `xinput set-prop "Device Enabled" 0` | ✗ | X11 only, also kills the device |
| libinput `AttrTrackpointMultiplier` / udev `POINTINGSTICK_SENSITIVITY` | ✗ | Ignored on many Elantech devices |
| `xinput set-prop "Coordinate Transformation Matrix" 0 0 0 0 0 0 0 0 1` | ✓ | X11 only — useless under Wayland |
| **ZO-REDdot** | ✓ | Works on Wayland + X11, keeps buttons |

The only fix that actually works is to **grab the device at the kernel boundary** and drop the X/Y motion while re-emitting the button events through a fresh uinput pointer. 30 lines of Python. That's it.

## Install

```bash
git clone https://github.com/Jok0ne/zo-reddot.git
cd zo-reddot
./install.sh
```

The installer:

- installs `python3-evdev` (supports `dnf` / `apt-get` / `pacman`),
- copies `zo-reddot.py` to `/usr/local/bin/` and the unit to `/etc/systemd/system/`,
- enables and starts `zo-reddot.service`.

Root is required — exclusive grab on an input device and writing to `/dev/uinput` are privileged operations.

### Verify

```bash
systemctl status zo-reddot
journalctl -u zo-reddot -f
```

Expected log line:

```text
zo-reddot: grabbed + uinput up — buttons only, motion dropped
```

Nudge the red dot: nothing. Click any of the three buttons under the spacebar: normal left / middle / right click.

## How it works

```text
  ┌────────────────────────┐
  │    TrackPoint device   │  /dev/input/event4
  │   (Elantech ISA PS/2)  │  emits:  BTN_LEFT/RIGHT/MIDDLE  +  EV_REL(X,Y)
  └────────────┬───────────┘
               │  device.grab() — exclusive read
               ▼
  ┌────────────────────────┐
  │       zo-reddot        │  forward:  BTN_LEFT/RIGHT/MIDDLE
  │     event  filter      │  drop:     EV_REL X/Y, scroll emulation
  └────────────┬───────────┘
               │  UInput.write_event() + syn()
               ▼
  ┌────────────────────────┐
  │ "TrackPoint Buttons    │  new /dev/input/eventN
  │  Only" (uinput device) │  advertises only BTN_LEFT/RIGHT/MIDDLE
  └────────────┬───────────┘
               │
               ▼
  ┌────────────────────────┐
  │    libinput +          │  buttons integrate normally,
  │    Wayland / X11       │  no pointer motion
  └────────────────────────┘
```

libinput and the desktop environment see the new uinput device as a normal button-only pointer and integrate it automatically. The pointing-stick itself has no visible consumer anymore, so nudging it does nothing.

Service survives reboots. Uninstall releases the device cleanly and restores the original behaviour.

## Configuration

The service matches the input device by exact name. Default:

```ini
TRACKPOINT_NAME=ETPS/2 Elantech TrackPoint
```

If your device has a different name — find it with `cat /proc/bus/input/devices` or `sudo libinput list-devices` — set `TRACKPOINT_NAME` in `/etc/systemd/system/zo-reddot.service`:

```ini
Environment=TRACKPOINT_NAME=TPPS/2 Elan TrackPoint
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart zo-reddot
```

## Uninstall

```bash
./install.sh uninstall
```

Stops and disables the service, removes the script and unit file. Original TrackPoint behaviour (pointer + buttons) is back immediately.

## Hardware

<table>
  <thead>
    <tr><th>Device</th><th>Digitizer</th><th>Tested on</th><th>Status</th></tr>
  </thead>
  <tbody>
    <tr>
      <td>ThinkPad Yoga 370</td>
      <td><code>Elantech 056a:50b0</code></td>
      <td>Fedora 42, Plasma 6 Wayland</td>
      <td align="center">✓</td>
    </tr>
    <tr>
      <td>T470 / T470s / T470p</td>
      <td>Elantech</td>
      <td>—</td>
      <td align="center">likely</td>
    </tr>
    <tr>
      <td>X270 / L470</td>
      <td>Elantech</td>
      <td>—</td>
      <td align="center">likely</td>
    </tr>
    <tr>
      <td>X1 Carbon Gen 5 / X1 Yoga Gen 2</td>
      <td>Elantech</td>
      <td>—</td>
      <td align="center">likely</td>
    </tr>
  </tbody>
</table>

If you run it successfully on other hardware, a PR adding to this list is welcome.

### What this does **not** touch

- Touchpad — separate input device.
- External USB / Bluetooth mice.
- Keyboard.
- Plasma / GNOME pointer-speed settings on every other pointer.

## Troubleshooting

<details>
<summary><b>The service is active but the TrackPoint still moves the cursor</b></summary>

<br>

libinput may have cached the original device. Log out and back in, or force a full config reload:

```bash
qdbus-qt6 org.kde.KWin /KWin reconfigure
```

If it still moves, verify the daemon grabbed the right device:

```bash
journalctl -u zo-reddot -n 20
```

You should see `grabbing /dev/input/eventN (<device name>)`. If `no input device named '…' found` appears instead, your TrackPoint has a different name — set `TRACKPOINT_NAME` as described in [Configuration](#configuration).

</details>

<details>
<summary><b>I have a different TrackPoint brand (Synaptics, IBM, ALPS)</b></summary>

<br>

Find the exact device name:

```bash
cat /proc/bus/input/devices | grep -iE "trackpoint|pointing"
```

Then set `TRACKPOINT_NAME` in the unit file. Common values:

- `TPPS/2 Elan TrackPoint`
- `TPPS/2 IBM TrackPoint`
- `Synaptics TM2334-004`
- `AlpsPS/2 ALPS DualPoint Stick`

</details>

<details>
<summary><b>GNOME / Cinnamon / XFCE / Sway support</b></summary>

<br>

ZO-REDdot operates at the kernel/uinput layer, below every desktop environment and display server. Anything that speaks libinput or evdev sees the buttons-only device and treats it as a normal button pointer. No desktop-specific configuration needed.

</details>

<details>
<summary><b>The service enters restart loop</b></summary>

<br>

The daemon exits with code 1 if it can't find the matching device. In a restart loop, this usually means the `TRACKPOINT_NAME` is wrong or the device was renamed after a kernel update. Disable auto-restart temporarily to debug:

```bash
sudo systemctl stop zo-reddot
sudo /usr/bin/python3 /usr/local/bin/zo-reddot.py
```

Read the stderr output, correct the env var, and restart.

</details>

## Design notes

### Why not `interception-tools` or the C `trackpoint-filter`?

Both work. ZO-REDdot exists because:

- **Zero compilation.** One Python file, done.
- **Readable source** — ~30 lines you can audit before running as root.
- **Single dependency** (`python3-evdev`) that every distro packages.
- **One process, one syscall loop** — no cascading dependency services.

If you need maximum efficiency, a compiled C equivalent saves ~15 MB of Python RSS. For a background daemon on a modern laptop, that tradeoff is usually fine.

### Why run as root?

`EVIOCGRAB` (exclusive device grab) and writing to `/dev/uinput` both require `CAP_SYS_ADMIN` or explicit input-group access plus uaccess. We could drop to a dedicated user with those capabilities, but root + `SupplementaryGroups=input` is clearer and the attack surface is ~30 lines of code.

### Why intercept instead of transform?

X11's `Coordinate Transformation Matrix` zeros out motion at the server level and leaves buttons alone — elegant, but bound to X11. Wayland has no equivalent primitive exposed to userspace. Kernel-level grab + uinput re-emit works on both, with the same latency as any other input device.

## License

**GPL-3.0-or-later** — see [`LICENSE`](LICENSE).

Copyright © 2026 Zerone. If you redistribute this — modified or not —
recipients must keep the same freedoms you received: attribution preserved,
source available, changes released under the same terms.

```text
SPDX-License-Identifier: GPL-3.0-or-later
```
