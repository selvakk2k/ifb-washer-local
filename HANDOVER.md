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
* **User Option / Modifier Command (9 bytes - Type 0x02)**:
  `63 07 02 00 <hil_id> <option_val> 00 <chk1> <chk2>`
  *(For `hil_id` in {5, 9}: `option_val` is written to byte 6; for all other options including 6, 7, 8, 12, 13, 14, 16, 18, 19, 21: `option_val` is placed at byte 5).*
  - `HIL_OPTION_RAPID_WASH`: `4`
  - `HIL_OPTION_PRE_WASH`: `6`
  - `HIL_OPTION_EXTRA_RINSE`: `7` (0–3 rinses)
  - `HIL_OPTION_RINSE_HOLD`: `8`
  - `HIL_OPTION_HOT_RINSE`: `12`
  - `HIL_OPTION_TIME_SAVER`: `13`
  - `HIL_OPTION_ECO`: `14`
  - `HIL_OPTION_ANTI_CREASE`: `16`
  - `HIL_OPTION_DRY`: `18` (0=Off, 1=Cupboard, 2=Iron, 3=Eco, 4=Gentle, 5=Time)
  - `HIL_OPTION_STEAM`: `19`
  - `HIL_OPTION_AROMA`: `21`
  - `HIL_OPTION_WARM_SOAK`: `22`
* **Fixed Commands (12 bytes)**:
  - Play: `63 0a 01 00 01 01 00 00 00 00 70 e6`
  - Pause: `63 0a 01 00 01 03 00 00 00 00 72 e8`
  - Cancel / Stop: `63 0a 01 00 01 04 00 00 00 00 73 e9`
  - Power On: `63 0a 01 00 01 11 00 00 00 00 80 f6`
  - Power Off: `63 0a 01 00 01 12 00 00 00 00 81 f7`

### Telemetry Status Frame Decoding (38 bytes)
* **Byte 7**: Bit 6 = Standby polarity (0 = Powered ON, 1 = Standby OFF).
* **Byte 9**: `extraRinse` count (0 = None, 1 = +1, 2 = +2, 3 = +3).
* **Byte 11 (`option2` bitmask)**:
  - Bit 2: Rinse Hold
  - Bit 3: Anti-Crease
  - Bit 6: Aroma
  - Bit 9: Steam
* **Byte 28**: `dryerOptions` code (0 = Off, 1 = Cupboard Dry, 2 = Iron Dry, 3 = Eco Dry, 4 = Gentle Dry, 5 = Time Dry).
* **Byte 29 (`optionEnable1` bitmask)**:
  - Bit 0: Pre-wash
  - Bit 1: Soak
  - Bit 2: Warm Soak
  - Bit 3: Hot Rinse
  - Bit 4: Time Saver
  - Bit 6: Eco
  - Bit 7: Rapid Wash

### Checksum Calculation
The two trailing bytes are computed using signed-byte accumulation across all preceding bytes (`data[:-2]`):
```python
def compute_checksums(data: bytes | list[int]) -> tuple[int, int]:
    s = sum(b if b < 128 else b - 256 for b in data) & 0xFFFF
    chk1 = s & 0xFF
    chk2 = (s * 2) & 0xFF
    return chk1, chk2
```

---

## 3. Verified Hardware Program Codes (`WD EXECUTIVE ZXS`)

The physical selector dial has 14 click positions arranged sequentially into two arcs:
* **Right Arc (Codes 1–7)**: Wash + Dry 2Hr (1), Wash + Dry 4Hr (2), Steam & Dry (3), Refresh (4), Power Steam (5), CradleWash® (6), Wool (7).
* **Left Arc (Codes 8–15)**: Bulky (8), Baby Wear (9), Anti-Allergen (10), Synthetic (11), Cotton (12), Mix / Daily (13), Express 15' (14), Tub Clean (15).

| Code | Program Name | Dial Arc | Default Temp | Default Spin | Nominal Time | Notes / Flags |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| `1` | **Wash + Dry 2Hr** | Right | 40°C | 1000 RPM | 120 min | Dry flag enabled |
| `2` | **Wash + Dry 4Hr** | Right | 40°C | 1200 RPM | 240 min | Dry flag enabled |
| `3` | **Steam & Dry** | Right | 40°C | 1400 RPM | 90 min | Steam + Dry flags |
| `4` | **Refresh** | Right | Steam / Cold | 0 RPM | 30 min | Wrinkle/odour removal (No spin) |
| `5` | **Power Steam** | Right | 40°C | 800 RPM | ~90 min | Steam stain removal |
| `6` | **CradleWash®** | Right | 30°C | 400 RPM | 37 min | Gentle silk/delicates cycle |
| `7` | **Wool** | Right | 30°C | 800 RPM | ~43 min | Woolmark certified cycle |
| `8` | **Bulky** | Left | 40°C | 800 RPM | ~90 min | Bedding and curtains |
| `9` | **Baby Wear** | Left | 60°C | 1000 RPM | ~130 min | Sanitizing extra rinse |
| `10` | **Anti-Allergen** | Left | 60°C | 1000 RPM | ~115 min | High temp allergen removal |
| `11` | **Synthetic** | Left | 40°C | 800 RPM | ~75 min | Synthetics / easy care |
| `12` | **Cotton** | Left | 60°C | 1400 RPM | 163 min | Full cotton cycle |
| `13` | **Mix / Daily** | Left | 40°C | 1000 RPM | 72 min | Daily standard load |
| `14` | **Express 15'** | Left | Cold | 800 RPM | 15 min | Rapid cycle |
| `15` | **Tub Clean** | Left | 95°C | 1400 RPM | ~90 min | App-designated sanitation cycle |

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

## 5. Telemetry Signature Auto-Detection Engine (Fallback / Experimental)

For unverified models or unknown dial configurations where physical layout is untested, the integration includes a fallback engine to reverse-engineer cycle identity by matching initial telemetry parameters against known signatures:

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

The setup flow in `config_flow.py` guides the user through setup:

```
[Step 1: IP & Port] -> [Step 2: Family Selection] -> [Step 3: Model Selection] -> [Step 4: Verification Wizard] -> [Entry Created]
                                                                                ↳ [Skip Verification]          ↗
```

1. **Step 2 (Family Selection)**:
   - Dropdown options:
     - `Washer Dryer (WD Executive / ZXS Series)`
     - `Front Load (Senator / Executive Plus Series)`
     - `Smart Top Load (SWID / SID Series) - Unverified`

2. **Step 3 (Model Selection)**:
   - Select exact catalog model or enter custom model name.

3. **Step 4 (Sequential Dial Verification)**:
   - **Phase 1 (Same-Side Test)**: Probes another program on the same dial arc (Right 1–7 or Left 8–15) as the currently active program. If the washer is actively running or paused, the probe is safely skipped to avoid disrupting the cycle.
   - **Phase 2 (Opposite-Side Test)**: Probes a candidate program on the opposite dial arc.
   - **Skip Option**: Users can skip verification at any step to immediately complete setup.

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
  - Selectors: Program dropdown, Spin Speed chips, Temperature chips, Extra Rinse chips, Dry Mode chips.
  - Modifiers: Pre-wash, Soak, Rinse Hold, Time Saver, Hot Rinse, Eco, Steam, Aroma, Anti-Crease toggle chips.

---

## 9. Codebase Structure

```
ifb-washer-local/
├── ifb_washer_local/                           # Standalone async client library (PyPI)
│   ├── client.py                               # IFBWasherClient (HTTP multipart POST with asyncio.Lock)
│   ├── const.py                                # Constants, Enums, Program & Signature tables
│   ├── exceptions.py                           # Custom exceptions
│   ├── protocol.py                             # Binary encoders, decoders, checksums
│   └── __init__.py                             # Package exports
├── custom_components/ifb_washer_local/         # Home Assistant integration (HACS)
│   ├── ifb_washer_local/                       # Vendored local copy with fallback imports
│   ├── __init__.py                             # Config entry setup & platform forwarding
│   ├── config_flow.py                          # Setup flow: family selection, safe dial check, skip
│   ├── coordinator.py                          # Adaptive polling coordinator (options-driven)
│   ├── sensor.py                               # State, Program, Remaining, RPM, Temp, Timestamp, Progress
│   ├── binary_sensor.py                        # Running, Door, Child Lock, Problem
│   ├── select.py                               # Program, Spin Speed, Temp, Delay, Extra Rinse, Dry Mode
│   ├── button.py                               # Start, Pause, Cancel buttons
│   ├── switch.py                               # Power, Child Lock, and 9 Cycle Modifier switches
│   ├── manifest.json                           # HACS / Core manifest
│   └── strings.json / translations/            # Localization strings
└── tests/                                      # Pytest test suite
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
