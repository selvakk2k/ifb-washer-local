# IFB Washer Local Integration (`ifb-washer-local`)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/github/v/release/selvakk2k/ifb-washer-local?style=flat-square)](https://github.com/selvakk2k/ifb-washer-local/releases)
[![AI-Assisted](https://img.shields.io/badge/AI%20Assisted-Antigravity%20%7C%20Claude-blueviolet?style=flat-square&logo=google)](https://github.com/selvakk2k)
[![AI Attribution](https://img.shields.io/badge/AI%20Attribution-AIA%20PAI%20Nc%20Hin-orange?style=flat-square)](https://aiattribution.github.io/interpret-attribution)

Zero-cloud, 100% local Home Assistant integration and standalone Python library for IFB front-load washing machines and washer dryers. 

Directly communicates with the internal Wi-Fi module on port 80 over your local home network without requiring cloud accounts, mobile apps, SMS OTPs, or active internet connectivity.

## Table of Contents
* [Features](#features)
* [Hardware Compatibility](#hardware-compatibility)
* [Network Architecture](#network-architecture)
* [Installation](#installation)
  * [Option 1: HACS Custom Repository](#option-1-hacs-custom-repository)
  * [Option 2: Manual Installation](#option-2-manual-installation)
* [Configuration](#configuration)
* [Entities Provided](#entities-provided)
* [Python Library Usage](#python-library-usage)
* [Credits & License](#credits--license)

---

## Features

* **100% Local Control**: Direct LAN HTTP communication on port 80 with the washer's internal controller. No external cloud dependence.
* **Instant Telemetry**: Live updates for cycle progress, remaining duration, active program, motor speed (RPM), and water temperature.
* **Full Remote Controls**: Start, pause, cancel, and turn off the machine directly from Home Assistant.
* **Option Customization**: Remote selection of wash programs, spin speed, temperature, and child lock toggling.
* **Adaptive Polling**: Automatically speeds up polling intervals during active wash cycles (every 5 seconds) and relaxes while idle in standby (every 15 seconds) to minimize local network traffic.
* **Zero Authentication Friction**: Direct binary packet communication eliminates expired auth tokens and cloud outages.

---

## Hardware Compatibility

| Model Series | Connectivity | Tested Functionality | Status |
| :--- | :--- | :--- | :--- |
| IFB Washer Dryer 742 Series | Local Wi-Fi (Port 80) | Live Telemetry, Program Selection, Child Lock, Start/Pause | ✅ Hardware Verified |
| IFB Front Load Senator / Executive Series | Local Wi-Fi (Port 80) | Status telemetry and basic controls | ⚠️ Experimental |
| IFB Top Load Washers | Local Wi-Fi (Port 80) | Status query frame supported | ⚠️ Experimental |

---

## Network Architecture

The washing machine exposes an embedded HTTP server on local port 80 at `/gainspan/profile/ifb`. Commands and queries are transmitted as raw binary frames within multipart HTTP POST requests:

```
Home Assistant / Python Client
       │
       ▼ (HTTP POST /gainspan/profile/ifb?t=<timestamp>)
Local Home Network (Port 80)
       │
       ▼
IFB Wi-Fi Controller (GainSpan / Realtek Module)
       │ (UART / Serial)
Main Machine Control Board (MCU)
```

Frame validation is enforced by a two-byte checksum calculated using signed-byte accumulation.

---

## Installation

### Option 1: HACS Custom Repository

1. In Home Assistant, open **HACS** > **Integrations**.
2. Click the top-right menu and select **Custom repositories**.
3. Enter `https://github.com/selvakk2k/ifb-washer-local`, select category **Integration**, and click **Add**.
4. Search for **IFB Washer Local** and select **Download**.
5. Restart Home Assistant.

### Option 2: Manual Installation

1. Download the latest release from GitHub.
2. Copy the `custom_components/ifb_washer_local` folder into your Home Assistant `<config>/custom_components/` directory.
3. Restart Home Assistant.

---

## Configuration

1. In Home Assistant, navigate to **Settings** > **Devices & Services**.
2. Click **Add Integration** and search for **IFB Washer Local**.
3. Enter the local IP address assigned to your washing machine (e.g. `192.168.0.100`) and click **Submit**.
4. *(Recommended)* Reserve a static IP for your washing machine in your home Wi-Fi router settings.

---

## Entities Provided

### Sensors
* **Machine State**: Current cycle phase (Standby, Pre-wash, Main Wash, Rinse, Final Spin, Complete, etc.)
* **Active Program**: Selected wash cycle (Mix / Daily, Cotton, Tub Clean, etc.)
* **Time Remaining**: Cycle countdown in minutes.
* **Motor Speed**: Real-time drum rotation speed in RPM.
* **Water Temperature**: Water temperature in drum (°C).
* **Selected Spin Speed**: Configured spin speed option.
* **Selected Temperature**: Configured wash temperature option.

### Binary Sensors
* **Running**: Indicates whether a cycle is actively running.
* **Door**: Door lock security state (Locked / Unlocked).
* **Child Lock Active**: Physical control panel lockout status.

### Selectors
* **Program**: Remote selection of wash programs (`select.program_select`).
* **Spin Speed**: Remote adjustment of spin speed (`select.spin_speed_select` - No Spin, 400, 600, 800, 1000, 1200, 1400 RPM).
* **Temperature**: Remote adjustment of wash temperature (`select.temperature_select` - Cold, 30°C, 40°C, 60°C, 95°C).
* **Delay Start**: Remote selection of delay start timer (`select.delay_start_select` - No Delay, 30 Min, 1 to 19 Hours).

### Controls
* **Power Switch**: Toggle washer power state (`switch.power` - On / Low-power Standby).
* **Child Lock Switch**: Toggle physical control panel lock (`switch.child_lock_switch`).
* **Start Button**: Start or resume wash program (`button.start`).
* **Pause Button**: Pause running wash program (`button.pause`).
* **Cancel Button**: Terminate the current cycle (`button.cancel`).

---

## Python Library Usage

The companion `ifb_washer_local` library can be used independently of Home Assistant in any Python script:

```python
import asyncio
from ifb_washer_local import IFBWasherClient

async def main():
    async with IFBWasherClient(host="192.168.0.100") as client:
        # Read live state
        state = await client.get_state()
        print(f"Program: {state.program_name}")
        print(f"Time Remaining: {state.remaining_minutes} min")
        print(f"State: {state.state_name}")
        print(f"Child Lock: {state.child_lock}")

        # Select Mix / Daily program (Code 13)
        await client.select_program(program_code=13)

        # Toggle Child Lock
        await client.set_child_lock(True)

asyncio.run(main())
```

---

## Credits & License

### Project Contributors & AI Attribution
* **Lead Architecture & Hardware Validation**: [@selvakk2k](https://github.com/selvakk2k) — physical testing on hardware, architectural design, and domain requirements.
* **Code Implementation & Engineering**: **Antigravity** (Google DeepMind) — core algorithm development, Home Assistant platform migrations, async concurrency architecture, and automated test suites.
* **Pre-Release Code Review & Auditing**: **Claude** (Anthropic) — independent architectural review, edge-case analysis, and verification of upstream compatibility.

Licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.
