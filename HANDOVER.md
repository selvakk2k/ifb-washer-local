# Project Handover: IFB Washer Local (`ifb-washer-local`)

This document serves as the primary technical context, protocol reference, and architectural briefing for any developer or AI coding agent working on the `ifb-washer-local` repository and its companion custom Lovelace card.

---

## 1. Executive Summary & Hardware Verification

* **Repository Goal**: 100% local, zero-cloud Home Assistant integration and standalone Python library (`ifb_washer_local`) for IFB smart washing machines and washer dryers.
* **Primary Target Device**: IFB Front Load Washer Dryer (`WD EXECUTIVE ZXS`, 7kg wash / 4kg dry).
* **Target IP**: `192.168.0.100:80` (Static DHCP reservation on local network).
* **Wi-Fi Controller**: GainSpan / Realtek embedded Wi-Fi module (`20:f8:5e:5d:59:0b`).
* **Verification Milestones**:
  - Direct local HTTP communication verified on port 80 (`/gainspan/profile/ifb`).
  - Active POST polling validated to force immediate UART status retrieval from MCU.
  - Complete 14-position physical clockwise selector dial rotation executed on live hardware, mapping all 15 program codes.
  - Bidirectional controls validated (Child Lock toggling, remote program switching, Start/Pause).

---

## 2. LAN Protocol & GainSpan Endpoint Mechanics

The washing machine's GainSpan module hosts an embedded web server on port 80.

### Critical Discovery: Active POST vs. Cached GET
* **`GET /gainspan/profile/ifb`**: Returns only the last cached buffer in the GainSpan module. If the machine has not pushed an unsolicited async update, this buffer goes stale or returns all zeros (`00`s).
* **`POST /gainspan/profile/ifb?t=<timestamp_ms>`**: Passing the 12-byte status query packet forces the GainSpan module to query the main motor control unit (MCU) over internal UART and returns the live 38-byte frame synchronously:
  ```
  POST http://192.168.0.100:80/gainspan/profile/ifb?t=1725807123456
  Content-Type: multipart/form-data; boundary=---------------------------974767299852498929531610575
  Body: 12-byte query packet
  ```

### Standard Command Packets
* **Active Status Query (12 bytes)**:
  `63 0a 01 00 01 07 00 00 00 00 76 ec`
* **Program Selection (21 bytes)**:
  `63 13 03 00 00 <prog_id> 00 <spin_code> 00 <temp_code> 00 00 00 00 <child_lock> 00 00 00 00 <chk1> <chk2>`
* **Fixed Commands (12 bytes)**:
  - Play: `63 0a 01 00 01 01 00 00 00 00 70 e6`
  - Pause: `63 0a 01 00 01 03 00 00 00 00 72 e8`
  - Cancel / Stop: `63 0a 01 00 01 04 00 00 00 00 73 e9`
  - Power Off: `63 0a 01 00 01 12 00 00 00 00 81 f7`

### Checksum Calculation
The two trailing bytes are computed using signed-byte accumulation across all preceding bytes (`data[:-2]`):
```python
def compute_checksums(data: bytes | list[int]) -> tuple[int, int]:
    s = sum(b if b < 128 else b - 256 for b in data) & 0xFFFF
    chk1 = s & 0xFF
    chk2 = (s * 2) & 0xFF if s < 249 else int(f"{s:02x}"[-2], 16)
    return chk1, chk2
```

---

## 3. Verified Hardware Program Codes (`WD EXECUTIVE ZXS`)

The physical selector dial has 14 click positions. Rotation begins clockwise from position 1:

| Code | Program Name | Default Temp | Default Spin | Nominal Time | Notes / Flags |
| :---: | :--- | :---: | :---: | :---: | :--- |
| `1` | **Wash + Dry 2Hr** | 40°C | 1000 RPM | 120 min | Dry flag enabled |
| `2` | **Wash + Dry 4Hr** | 40°C | 1200 RPM | 240 min | Dry flag enabled |
| `3` | **Steam & Dry** | 40°C | 1400 RPM | 90 min | Steam + Dry flags |
| `4` | **Refresh** | Steam / Cold | 0 RPM | 30 min | Wrinkle/odour removal (No spin) |
| `5` | **Power Steam** | 40°C | 800 RPM | ~90 min | Steam stain removal |
| `6` | **CradleWash®** | 30°C | 400 RPM | 37 min | Gentle silk/delicates cycle |
| `7` | **Wool** | 30°C | 800 RPM | ~43 min | Woolmark certified cycle |
| `8` | **Bulky** | 40°C | 800 RPM | ~90 min | Bedding and curtains |
| `9` | **Baby Wear** | 60°C | 1000 RPM | ~130 min | Sanitizing extra rinse |
| `10` | **Anti-Allergen** | 60°C | 1000 RPM | ~115 min | High temp allergen removal |
| `11` | **Synthetic** | 40°C | 800 RPM | ~75 min | Synthetics / easy care |
| `12` | **Cotton** | 60°C | 1400 RPM | 163 min | Full cotton cycle |
| `13` | **Mix / Daily** | 40°C | 1000 RPM | 72 min | Daily standard load |
| `14` | **Express 15'** | Cold | 800 RPM | 15 min | Rapid cycle |
| `15` | **Tub Clean** | 95°C | 1400 RPM | ~90 min | App-designated sanitation cycle |

---

## 4. Appliance Families & Program Matrices

The codebase supports three distinct families:

### A. `WASHER_DRYER` (Hardware Verified)
Uses the 15 verified codes listed above.

### B. `FRONT_LOAD` (Senator / Executive Plus Series)
Extracted from official manual `FL_790_G_Manual_Digital.pdf`:
* **Dial Cycles**: Mix/Daily, Cotton, Uniform/Linen, Baby Wear, Anti-Allergen, Express 30', Express 15', Refresh, Wool, Synthetic, CradleWash®, Bulky/Bedding.
* **App-Exclusive Cycles ("PROGRAMS VIA MY IFB APP")**: Sports Wear, Dark Wash, Jeans, PowerSteam®, Inner Wear, Shirts, Tub Clean, Spin Dry/Rinse.

### C. `TOP_LOAD_SMART` (`SWID` / `SID` Series - Marked Unverified)
Extracted from official manual `TL_360_UM.pdf`:
* **Dial / Front Touch Cycles**: Mix/Daily, Cotton, Express 30', Synthetic, Delicates, StainFighter™, Bulky, Anti-Allergen, Rinse+Spin, Tub Clean.
* **App-Exclusive Cycles**: Saree, Baby Wear, Uniform, Jeans, Sports Wear.
* **Telemetry Difference**: Uses Water Levels (1 to 10), Wash Time (0–20m), Rinse Count (0–5), and Spin Time (0–9m) rather than discrete spin RPMs.

---

## 5. Telemetry Signature Auto-Detection Engine

When an unverified model or unknown program code is probed, the integration can reverse engineer its identity by matching the initial telemetry tuple `(duration_min, temp_c, spin_rpm, is_dry_enabled)` against official manual specifications:

| Program Signature | Duration | Temp | Spin | Dry Flag |
| :--- | :---: | :---: | :---: | :---: |
| **Express 15'** | 15 min | Cold (0°C) | 800 RPM | No |
| **Refresh** | 30 min | Cold (0°C) | 0 RPM | No |
| **CradleWash®** | 37 min | 30°C | 400 RPM | No |
| **Wool** | ~43 min | 30°C | 800 RPM | No |
| **Mix / Daily** | ~72 min | 40°C | 1000 RPM | No |
| **Anti-Allergen** | ~115 min | 60°C | 1000 RPM | No |
| **Cotton** | ~163 min | 60°C | 1400 RPM | No |
| **Wash + Dry 2Hr** | 120 min | 40°C | 1000 RPM | Yes |
| **Wash + Dry 4Hr** | 240 min | 40°C | 1200 RPM | Yes |

---

## 6. Config Flow & Verification Wizard Specification

The setup flow in `config_flow.py` must support the following step progression:

```
[Step 1: IP & Port] -> [Step 2: Family Selection] -> [Step 3: Verification Wizard] -> [Entry Created]
                                                  ↳ [Step 4: Manual Code Form]   ↗
```

1. **Step 2 (Family Selection)**:
   - Dropdown options:
     - `Washer Dryer (WD Executive / ZXS Series)`
     - `Front Load (Senator / Executive Plus Series)`
     - `Smart Top Load (SWID / SID Series) - Unverified`
     - `Manual / Custom Configuration`
     - `Auto-Detect from Telemetry`

2. **Step 3 (Interactive Visual Verification)**:
   - Instructions: *"Please stand next to your washing machine to verify the display."*
   - Test 1 (Left Program): Sends command `0x03` for Code `13` (Mix/Daily). Asks: *"Does the display show 'Mix / Daily'?"*
   - Test 2 (Right Program): Sends command `0x03` for Code `1` (Wash+Dry 2Hr) or Code `14` (Express 15'). Asks: *"Does the display show '[Target Program]'?"*
   - **Skip Option**: Includes a *"Skip visual verification"* checkbox so users not near the appliance can finish setup immediately.

3. **Step 4 (Manual Code Form)**:
   - Accessible if the user selects `Manual / Custom Configuration` or fails visual verification.
   - Provides numeric input fields for assigning custom program codes.

---

## 7. Home Assistant Platform Gap Analysis

To match standard appliance integrations (Bosch Home Connect, Miele, LG ThinQ):

1. **Estimated End Time Sensor (`device_class: timestamp`)**:
   - Current: Only `time_remaining` in static minutes (`SensorDeviceClass.DURATION`).
   - Implementation: Return `utcnow() + timedelta(minutes=remaining_minutes)` when machine is running. Home Assistant Lovelace renders this as a real-time relative countdown in the browser.
2. **Progress Percentage Sensor (`device_class: percentage`)**:
   - Implementation: Return `((initial_duration - remaining_minutes) / initial_duration) * 100`.
3. **Problem / Fault Binary Sensor (`device_class: problem`)**:
   - Telemetry tracks error states: `tAP` (water tap closed), `drn` (drain failure), `door` (door open), `unb` (unbalanced load).
   - Implementation: `binary_sensor.<washer>_problem` with `error_code` attribute.
4. **Maintenance Counter (Washes Since Tub Clean)**:
   - Track completed wash cycles and alert user when count exceeds 35-40 washes.

---

## 8. Custom Lovelace Card Architecture (`ifb-washer-card`)

When building the custom Lovelace card, follow the **Indian Smart Appliance Design System** (`appliance_lovelace_design_system`):

### Visual & Layout Tokens
* **Card Container**: Standard rounded corners (`border-radius: 16px`), subtle surface elevation, clear responsive padding (16px desktop, 12px mobile).
* **Drum Animation Component**:
  - Central circular drum SVG representation.
  - When `binary_sensor.running` is `true`: drum rotates clockwise with CSS animation speed proportional to `sensor.motor_rpm` (gentle tumble during wash, rapid spin during final spin).
  - Center of drum displays live remaining time countdown (`sensor.time_remaining` / timestamp) and current stage chip (`Main Wash`, `Rinse`, `Final Spin`, `Drying`).
* **Status Badges**:
  - Door status chip (`Locked` / `Unlocked`).
  - Child Lock chip.
  - Steam active indicator.
* **Quick Action Controls**:
  - Primary button: Start / Pause (prominent floating accent button).
  - Secondary buttons: Power Off, Child Lock toggle.
  - Selectors: Program dropdown, Spin Speed chips (400, 800, 1000, 1200, 1400), Temperature chips (Cold, 30°, 40°, 60°, 95°).

---

## 9. Codebase Structure

```
ifb-washer-local/
├── ifb_washer_local/                   # Standalone async client library
│   ├── client.py                       # IFBWasherClient (HTTP multipart POST)
│   ├── const.py                        # Constants, Enums, Program & Signature tables
│   ├── exceptions.py                   # Custom exceptions
│   ├── protocol.py                     # Binary encoders, decoders, checksums
│   └── __init__.py                     # Package exports
├── custom_components/ifb_washer_local/ # Home Assistant integration
│   ├── __init__.py                     # Config entry setup & platform forwarding
│   ├── config_flow.py                  # Wizard: family selection, visual check, skip
│   ├── coordinator.py                  # Adaptive polling coordinator (5s run / 15s idle)
│   ├── sensor.py                       # State, Program, Remaining, RPM, Temp, Timestamp, Progress
│   ├── binary_sensor.py                # Running, Door, Child Lock, Problem
│   ├── select.py                       # Program, Spin Speed, Temp selectors
│   ├── button.py                       # Start, Pause, Cancel, Power Off buttons
│   ├── switch.py                       # Child Lock, Steam, Extra Rinse switches
│   ├── manifest.json                   # HACS / Core manifest
│   └── strings.json / translations/    # Localization strings
├── manuals/official/                   # 47 scraped official IFB user manuals
└── tests/
    └── test_protocol.py                # Pytest unit test suite
```

---

## 10. Git Commit & Attribution Standards

All commits authored or assisted by coding agents must include canonical co-authorship trailers:

```text
feat(protocol): Add verified program matrices and telemetry signatures

- Implemented 15-program verified layout for WD Executive series.
- Added Senator and Top Loader manual matrices.
- Added telemetry signature reverse-engineering database.

Co-authored-by: Claude <noreply@anthropic.com>
Co-authored-by: Antigravity <326255689+antigravity-selvakk2k[bot]@users.noreply.github.com>
```

Repository template reference: `/home/skk/.gemini/config/templates/attribution_and_license_template.md`.
Plain everyday English only; no decorative emojis in commits, code, or documentation.
