# Project Handover: IFB Washer Local (`ifb-washer-local`)

This document serves as the primary technical context and operational briefing for any developer or AI coding agent working on the `ifb-washer-local` repository.

---

## 1. Executive Summary & Hardware Verification

* **Repository Goal**: 100% local, zero-cloud Home Assistant integration and standalone Python library (`ifb_washer_local`) for IFB front-load washing machines and washer dryers.
* **Target Device**: IFB Front Load Washer Dryer (742 Series, 7kg wash / 4kg dry).
* **Network Address**: `192.168.0.100:80` (static DHCP reservation on LAN).
* **Wi-Fi Controller**: GainSpan / Realtek embedded Wi-Fi module (`20:f8:5e:5d:59:0b`).
* **Verification Status**:
  - Live local telemetry polling confirmed over HTTP port 80.
  - Bidirectional control validated on physical machine hardware (Child Lock toggled and verified in state; program remotely switched between Cotton and Mix / Daily with immediate display reflection on the machine LED panel).

---

## 2. LAN Protocol & Frame Specification

The machine's Wi-Fi module hosts an embedded HTTP server on port 80. Telemetry and commands are exchanged as raw binary payloads via multipart HTTP POST requests:

```
POST http://<washer-ip>:80/gainspan/profile/ifb?t=<timestamp_ms>
Content-Type: multipart/form-data
Body: <raw_binary_packet>
```

### Packet Framing
* **Header**: Byte 0 is always `0x63` (`99`).
* **Command Types**:
  - `0x01`: Fixed Machine Commands (Play = `0x01`, Pause = `0x03`, Cancel = `0x04`, Status Query = `0x07`, Power Off = `0x12`).
  - `0x02`: Hardware Interface Layer (HIL) Option Selection (Temperature = `3`, Spin = `5`, Extra Rinse = `7`, Delay = `9`, Soak = `10`, Child Lock = `11`).
  - `0x03`: Program Selection (21 bytes).

### Checksum Algorithm
The checksum consists of two trailing bytes calculated via signed-byte accumulation across all preceding bytes (`data[:-2]`):

```python
def compute_checksums(data: bytes | list[int]) -> tuple[int, int]:
    s = 0
    for b in data:
        signed_val = b if b < 128 else b - 256
        s += signed_val
    s = s & 0xFFFF
    chk1 = s & 0xFF
    if s < 249:
        chk2 = (s * 2) & 0xFF
    else:
        chk2 = int(f"{s:02x}"[-2], 16)
    return chk1, chk2
```

---

## 3. Hardware Verified Programs & Mapping (742 Series)

Do not use cloud integration program tables blindly, as different IFB models use different program index maps. The following program codes have been verified directly on 742 series hardware:

| Program Code | Program Name | Default Display Time | Default Spin | Default Temp | Verification |
| :---: | :--- | :---: | :---: | :---: | :---: |
| `12` (`0x0C`) | **Cotton** | `2h 43m` (163 min) | Option `8` (1200/1400) | Option `4` (40°C) | ✅ Physically verified via dial |
| `13` (`0x0D`) | **Mix / Daily** | `1h 12m` (72 min) | Option `6` (1000 RPM) | Option `2` (Cold) | ✅ Remote switch & dial verified |
| `14` (`0x0E`) | **Tub Clean** | ~`1h 50m` | Option `6` | Option `6` (95°C) | ✅ App/Remote designated cycle |

### Telemetry Frame Byte Map (38-byte response)
* `data[0]`: Header (`0x63`)
* `data[1]`: Length (`0x24` = 36 payload bytes)
* `data[2]`: ACK Code (`0x81` for query response, `0x83` for command response)
* `data[6]`: Active Program Code (`12` = Cotton, `13` = Mix / Daily)
* `data[8]`: Selected Spin Speed Option (`0`=No spin, `1`=400, `2`=600, `4`=800, `6`=1000, `7`=1200, `8`=1400)
* `data[10]`: Selected Temperature Option (`2`=Cold, `3`=30°C, `4`=40°C, `5`=60°C, `6`=95°C)
* `data[15]`: Child Lock Active (`0` = Off, `1` = Locked)
* `data[17]`: Remaining Time Hours
* `data[18]`: Remaining Time Minutes
* `data[19:21]`: Motor Speed (RPM, big-endian unsigned 16-bit integer)
* `data[21]`: Water Temperature (°C)
* `data[30]`: Machine State Enum (`1` = Standby, `2` = Starting, `4` = Main Wash, `11` = Final Spin, `13` = Complete, `14` = Paused)
* `data[31]`: Door Status (`1` = Closed/Locked)
* `data[-2:]`: Two-byte Checksum (`chk1`, `chk2`)

---

## 4. Codebase Architecture

```
ifb-washer-local/
├── ifb_washer_local/                   # Standalone async client library
│   ├── client.py                       # IFBWasherClient (aiohttp LAN HTTP)
│   ├── const.py                        # Constants, Enums, Program tables
│   ├── exceptions.py                   # Custom error classes
│   ├── protocol.py                     # Binary encoders, decoders, checksums
│   └── __init__.py                     # Clean library exports
├── custom_components/ifb_washer_local/ # Home Assistant custom component
│   ├── __init__.py                     # Entry setup / unload
│   ├── config_flow.py                  # Single-step IP configuration flow
│   ├── coordinator.py                  # Adaptive polling DataUpdateCoordinator (5s run / 15s idle)
│   ├── sensor.py                       # State, Program, Remaining Time, RPM, Temp
│   ├── binary_sensor.py                # Running, Door, Child Lock
│   ├── select.py                       # Program, Spin, Temp selectors
│   ├── button.py                       # Start, Pause, Cancel, Turn Off buttons
│   ├── switch.py                       # Child Lock switch
│   ├── manifest.json                   # HACS / HA integration manifest
│   └── strings.json / translations/    # Localization files
└── tests/
    └── test_protocol.py                # Full protocol unit tests (all passing)
```

---

## 5. Development Guidelines & Commit Attribution

* **Running Tests**: Run `python3 -m pytest -v` from the repository root.
* **Commit Trailers**: All commits must include canonical trailers:
  ```text
  Co-authored-by: Claude <noreply@anthropic.com>
  Co-authored-by: Antigravity <326255689+antigravity-selvakk2k[bot]@users.noreply.github.com>
  ```
* **Tone & Documentation**: Strictly follow plain everyday English without jargon. Never use decorative emojis (only functional `✅` / `⚠️` in tables).
