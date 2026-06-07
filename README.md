# VeryFit / WowME ID217G Sport Black - BLE Protocol Client

Python client for communicating with WowME ID217G Sport Black smartwatch via Bluetooth Low Energy (BLE). Reverse engineered from the VeryFit APK (v2.8.10).

## Features

- **Device Discovery**: Scan for nearby BLE devices
- **Pairing/Binding**: Two-phase bind protocol (BindPara + BindAuth)
- **Time Synchronization**: Set device clock to current time
- **User Profile**: Configure gender, weight, height, birth date
- **Daily Goals**: Set step, calorie, and distance targets
- **Health Data**: Request health data sync from device
- **Full Setup**: One-command complete device configuration

## Requirements

- Python 3.8+
- Linux (tested on Ubuntu/Debian)
- BLE adapter supported by BlueZ

## Quick Start

### 1. Setup

```bash
# Create virtual environment and install dependencies
make venv

# Or manually:
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Scan for Devices

```bash
make scan
# or
.venv/bin/python veryfit_client.py scan
```

### 3. Full Setup (Pair + Time + User Info + Goals)

```bash
make all DEVICE="WowME ID217G"
# or
.venv/bin/python veryfit_client.py all "WowME ID217G"
```

### 4. Individual Commands

```bash
make pair DEVICE="WowME ID217G"
make settime DEVICE="WowME ID217G"
make userinfo DEVICE="WowME ID217G"
make goal DEVICE="WowME ID217G"
make data DEVICE="WowME ID217G"
```

## Makefile Commands

| Command | Description | Example |
|---------|-------------|---------|
| `make help` | Show available commands | `make help` |
| `make venv` | Create virtual environment | `make venv` |
| `make run` | Run client with args | `make run args="scan"` |
| `make scan` | Scan for BLE devices | `make scan` |
| `make pair` | Pair with device | `make pair DEVICE="WowME ID217G"` |
| `make settime` | Set device time | `make settime DEVICE="WowME ID217G"` |
| `make userinfo` | Set user info | `make userinfo DEVICE="WowME ID217G"` |
| `make goal` | Set daily goals | `make goal DEVICE="WowME ID217G"` |
| `make data` | Request health data | `make data DEVICE="WowME ID217G"` |
| `make all` | Full setup | `make all DEVICE="WowME ID217G"` |
| `make lint` | Run ruff linter | `make lint` |
| `make clean` | Remove venv and cache | `make clean` |

## Manual Usage

```bash
# Run without Makefile
.venv/bin/python veryfit_client.py scan
.venv/bin/python veryfit_client.py pair "WowME ID217G"
.venv/bin/python veryfit_client.py settime "WowME ID217G"
.venv/bin/python veryfit_client.py userinfo "WowME ID217G"
.venv/bin/python veryfit_client.py goal "WowME ID217G"
.venv/bin/python veryfit_client.py data "WowME ID217G"
.venv/bin/python veryfit_client.py all "WowME ID217G"
```

## BLE Protocol Details

### Discovered UUIDs

| UUID | Purpose |
|------|---------|
| `00001101-0000-1000-8000-00805F9B34FB` | Primary service |
| `00000af4-0000-1000-8000-00805f9b34fb` | Write characteristic |
| `00000af0-0000-1000-8000-00805f9b34fb` | Notify characteristic |
| `00002902-0000-1000-8000-00805f9b34fb` | CCCD (enable notifications) |
| `0000fd50-0000-1000-8000-00805f9b34fb` | DFU service |
| `0000fe59-0000-1000-8000-00805f9b34fb` | Nordic UART service |

### Protocol Command Codes

| Command | Code | Description |
|---------|------|-------------|
| `CMD_BIND` | 9216 | Bind/Pair device |
| `CMD_USER_INFO` | 1000 | User profile info |
| `CMD_SYSTEM_TIME` | 5514 | Time synchronization |
| `CMD_GOAL` | 5000 | Daily activity goals |
| `CMD_HEALTH_DATA` | 1001 | Health data sync |
| `CMD_CONFIG_INFO` | 1002 | Configuration info |
| `CMD_ALARM` | 5001 | Alarm settings |
| `CMD_NOT_DISTURB` | 186 | Do not disturb mode |
| `CMD_HEART_RATE_INTERVAL` | 553 | Heart rate interval |
| `CMD_MESSAGE_NOTIFY` | 5006 | Message notification |
| `CMD_PHONE_CONTACTS` | 620 | Phone contacts sync |

### Bind/Pair Flow

1. **Phase 1 - BindPara**: Send `BindPara` with OS type (Android=2), OS version, clean data flag
2. **Response**: Device returns status code (0=success, 2=auth code required)
3. **Phase 2 - BindAuth**: Send `BindAuth` with authentication code array

### Data Format

- Protocol uses binary encoding with command code headers
- Format: `[cmd_code:4 bytes LE][data...]`
- Some payloads are JSON-serialized then encrypted (native library AES-based)

## Reverse Engineering Notes

### Source APK

- **File**: `VeryFit_2.8.10_APKPure.apk` (173MB)
- **Package**: `com.ido.life` / `com.veryfit`
- **Decompiled**: 29,370 Java classes via jadx

### Key Classes

| Class | Purpose |
|-------|---------|
| `com.ido.ble.BLEManager` | Main BLE manager |
| `com.ido.ble.bluetooth.e.f` | BLE UUID definitions |
| `com.veryfit.multi.nativeprotocol.b` | Command code constants |
| `com.ido.ble.protocol.model.SystemTime` | Time sync model |
| `com.ido.ble.protocol.model.UserInfo` | User info model |
| `com.ido.ble.protocol.model.BindPara` | Bind request model |
| `com.ido.ble.protocol.model.BindAuth` | Bind auth model |

### Native Libraries

- `libVeryFitMulti.so` - Native protocol library
- `libprotocol.so` - Protocol handling
- `libEncryptorP.so` / `libAesJni.so` - AES encryption

## Limitations

- Native library encryption not fully reversed (basic commands work)
- Health data parsing not implemented (device sends raw encrypted data)
- Only tested with WowME ID217G Sport Black (may work with other VeryFit devices)

## License

This project is for educational/research purposes only. Reverse engineering is done to enable interoperability with owned hardware.
