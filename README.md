# IFB Washer Local Integration (`ifb-washer-local`)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
[![Stable](https://img.shields.io/github/v/release/selvakk2k/ifb-washer-local?label=Stable&style=flat-square)](https://github.com/selvakk2k/ifb-washer-local/releases/latest)
[![Beta](https://img.shields.io/github/v/release/selvakk2k/ifb-washer-local?include_prereleases&label=Beta&color=orange&style=flat-square)](https://github.com/selvakk2k/ifb-washer-local/releases)
[![AI-Assisted](https://img.shields.io/badge/AI%20Assisted-Antigravity%20%7C%20Claude-blueviolet?style=flat-square&logo=google)](https://github.com/selvakk2k)
[![AI Attribution](https://img.shields.io/badge/AI%20Attribution-AIA%20PAI%20Nc%20Hin-orange?style=flat-square)](https://aiattribution.github.io/interpret-attribution)

Zero-cloud, 100% local Home Assistant custom integration for IFB front-load washing machines and washer dryers. 

Directly communicates with the internal Wi-Fi module on port 80 over your local home network without requiring cloud accounts, mobile apps, SMS OTPs, or active internet connectivity.

---

## Table of Contents
* [Features](#features)
* [Hardware Compatibility](#hardware-compatibility)
* [Network Architecture](#network-architecture)
* [Installation](#installation)
  * [Option 1: HACS Custom Repository](#option-1-hacs-custom-repository)
  * [Option 2: Manual Installation](#option-2-manual-installation)
* [Configuration](#configuration)
* [Hardware Profile Calibration & Standalone Backups](#hardware-profile-calibration--standalone-backups)
* [Entities Provided](#entities-provided)
* [Operation & Wash Guide](docs/WASH_GUIDE.md)
* [Companion Ecosystem & Models Database](#companion-ecosystem--models-database)
* [Credits & License](#credits--license)

---

## Features

* **100% Local Control**: Direct LAN HTTP communication on port 80 with the washer's internal controller. No external cloud dependence.
* **Instant Telemetry**: Live updates for cycle progress, remaining duration, active program, motor speed (RPM), and water temperature.
* **Full Remote Controls**: Start, pause, cancel, and turn off the machine directly from Home Assistant.
* **Option Customization**: Remote selection of wash programs, spin speed, temperature, extra rinse, dry modes, child lock, and wash modifiers (pre-wash, soak, steam, aroma, etc.).
* **Hardware Profile Calibration**: Automated, non-intrusive capability discovery directly from physical machine firmware for model-accurate program limits.
* **Standalone Profile Backups**: Automated JSON profile backups with privacy-safe host IP redaction and full UI Export/Import support.
* **Adaptive Polling**: Automatically speeds up polling intervals during active wash cycles (every 5 seconds) and relaxes while idle in standby (every 15 seconds) to minimize local network traffic.
* **Zero Authentication Friction**: Direct binary packet communication eliminates expired auth tokens and cloud outages.

---

## Hardware Compatibility

| Model Series | Connectivity | Tested Functionality | Status |
| :--- | :--- | :--- | :--- |
| IFB Washer Dryer 742 Series | Local Wi-Fi (Port 80) | Live Telemetry, Program Selection, Child Lock, Start/Pause, Heated Dry | ✅ Hardware Verified |
| IFB Front Load Senator / Executive Series | Local Wi-Fi (Port 80) | Status telemetry, Program Selection, and basic controls | ⚠️ Experimental |
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

### Option 1: Via HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=selvakk2k&repository=ifb-washer-local&category=integration)

1. Click the **Open repository in HACS** button above, or open **HACS** from your Home Assistant sidebar.
2. Click the top-right menu (⋮) → **Custom repositories** → Add `https://github.com/selvakk2k/ifb-washer-local` with category **Integration**.
3. Search for **IFB Washer Local**, click **Download**, and restart Home Assistant.

### Option 2: Manual Installation

1. Download the latest release from GitHub.
2. Copy the `custom_components/ifb_washer_local` folder into your Home Assistant `<config>/custom_components/` directory.
3. Restart Home Assistant.

---

## Configuration

1. In Home Assistant, navigate to **Settings** > **Devices & Services**.
2. Click **Add Integration** and search for **IFB Washer Local**.
3. Enter the local IP address assigned to your washing machine (e.g. `192.168.0.100`) and click **Submit**.
4. The integration automatically queries the appliance and presents the **Initial Capability Setup Wizard**:
   * **Use Models Database**: Automatically matches the model against the [`ifb-washer-models`](https://pypi.org/project/ifb-washer-models/) database for instant capability provisioning.
   * **Calibrate Hardware Now**: Run a live probe (Quick, Simple, or Detailed) directly against physical firmware while in Standby.
   * **Import Saved Profile**: Paste a previously exported JSON capability profile envelope.
   * **Skip (Safe Defaults)**: Use standard front-load / washer-dryer default limits.
5. *(Recommended)* Reserve a static DHCP IP address for your washing machine in your home Wi-Fi router settings.

---

## Hardware Profile Calibration & Standalone Backups

The integration can probe your physical appliance while in Standby to build a model-accurate capability map (allowed temperatures, spin speeds, dry modes, and modifiers per program).

### Running Calibration from Options
1. Navigate to **Settings** > **Devices & Services** > **IFB Washer Local** > **Configure**.
2. Choose **Calibrate Hardware Capabilities Profile** and select a probing mode:
   * **Quick (~2 minutes)**: Probes 8 core wash programs.
   * **Simple (~4-5 minutes)**: Probes all 14 standard dial programs.
   * **Detailed (~12-14 minutes)**: Full deep scan across all programs and modifier combinations with conservative delays.

### Standalone Profile Backups & Portability
* **Automatic Local File**: Calibrated profiles are automatically saved to `/config/ifb_washer_profiles/{model}_profile.json` inside your Home Assistant directory.
* **Export / View Active Profile**: View and copy the active profile JSON envelope directly from the Configure menu.
* **Restore / Import Profile**: Paste or restore any previously saved profile JSON to instantly configure capabilities without re-probing.
* **Privacy Safe**: All exported profile envelopes omit host IP addresses and network identifiers.

---

## Entities Provided

### Sensors
* **Machine State**: Current cycle phase (Standby, Pre-wash, Main Wash, Rinse, Final Spin, Complete, etc.)
* **Active Program**: Selected wash cycle (Mix / Daily, Cotton, Tub Clean, etc.). Dynamically exposes the active program's capability limits in `extra_state_attributes` (`allowed_temps`, `allowed_spins`, `allowed_dry_modes`, `steam_behavior`, modifiers) for dynamic Lovelace card filtering.
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
* **Temperature**: Remote adjustment of wash temperature (`select.temperature_select` - Cold, 20°C, 30°C, 40°C, 60°C, 95°C).
* **Delay Start**: Remote selection of delay start timer (`select.delay_start_select` - No Delay, 30 Min, 1 to 19 Hours).
* **Extra Rinse**: Remote selection of additional rinses (`select.extra_rinse_select` - 0 (None), +1 Rinse, +2 Rinses, +3 Rinses).
* **Dry Mode**: Remote selection of drying profiles on washer-dryer models (`select.dry_mode_select` - No Dry, Cupboard Dry, Iron Dry, 30 Minutes, 1 Hour, etc.).

### Controls
* **Power Switch**: Toggle washer power state (`switch.power` - On / Low-power Standby).
* **Child Lock Switch**: Toggle physical control panel lock (`switch.child_lock_switch`).
* **Modifier Switches**: Individual toggles for cycle modifiers:
  * **Pre-wash** (`switch.prewash_switch`)
  * **Soak** (`switch.soak_switch`)
  * **Rinse Hold** (`switch.rinse_hold_switch`)
  * **Time Saver** (`switch.time_saver_switch`)
  * **Hot Rinse** (`switch.hot_rinse_switch`)
  * **Eco** (`switch.eco_switch`)
  * **Steam** (`switch.steam_switch`)
  * **Aroma** (`switch.aroma_switch`)
  * **Anti-Crease** (`switch.anti_crease_switch`)
* **Start Button**: Start or resume wash program (`button.start`).
* **Pause Button**: Pause running wash program (`button.pause`).
* **Cancel Button**: Terminate the current cycle (`button.cancel`).

---

## Operation & Wash Guide

For a complete reference on all available programs (including Express 15', Refresh, and Spin Dry / Drain), allowed temperatures, spin speeds, drying modes, and cycle modifiers, see the [Operation & Wash Guide](docs/WASH_GUIDE.md).

---

## Companion Ecosystem & Models Database

* **Hardware Database & Program Gating**: For programmatic model lookups, rotary selector switch detents, and capability gating rules, see the companion package [`ifb-washer-models` on PyPI](https://pypi.org/project/ifb-washer-models/) and [GitHub](https://github.com/selvakk2k/ifb-washer-models).
* **Lovelace Frontend Card**: For the dynamic radial drum animation and smart appliance UI, install the companion [`ifb-washer-card`](https://github.com/selvakk2k/ifb-washer-card).
* **Wash Guide & Programs**: For detailed program cycle specifications and modifiers, consult the [Operation & Wash Guide](docs/WASH_GUIDE.md).

---

## My Integrations & Lovelace Cards

Explore companion integrations and custom cards tailored for Indian smart home appliances:

| Appliance Category | Home Assistant Integration | Companion Lovelace Card |
| :--- | :--- | :--- |
| **Air Conditioners** | [Panasonic AC India (`ha-miraie-ac-in`)](https://github.com/selvakk2k/ha-miraie-ac-in) | [Panasonic AC India Card (`miraie-ac-card-in`)](https://github.com/selvakk2k/miraie-ac-card-in) |
| **BLDC Ceiling Fans** | [Indian BLDC Fan IR (`superfan_ir`)](https://github.com/selvakk2k/superfan_ir) | [Indian BLDC Fan Card (`superfan-card`)](https://github.com/selvakk2k/superfan-card) |
| **Washing Machines** | [IFB Washer Local (`ifb-washer-local`)](https://github.com/selvakk2k/ifb-washer-local) | [IFB Washer Card (`ifb-washer-card`)](https://github.com/selvakk2k/ifb-washer-card) |
| **Smart Switches** | [Tinxy Local (`ha-tinxylocal`)](https://github.com/selvakk2k/ha-tinxylocal) | — |

---

## Credits & License

### Project Contributors & AI Attribution
* **Lead Architecture & Hardware Validation**: [@selvakk2k](https://github.com/selvakk2k) — physical testing on hardware, architectural design, and domain requirements.
* **Code Implementation & Engineering**: **Antigravity** (Google DeepMind) — core algorithm development, Home Assistant platform migrations, async concurrency architecture, and automated test suites.
* **Pre-Release Code Review & Auditing**: **Claude** (Anthropic) — independent architectural review, edge-case analysis, and verification of upstream compatibility.

Licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.
