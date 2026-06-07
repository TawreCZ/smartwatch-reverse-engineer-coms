# AGENTS.md

## Project Overview

This project reverse-engineers the VeryFit APK (2.8.10) to create a Python client for communicating with WowME ID217G Sport Black smartwatch via BLE.

## Quick Start

```bash
# Setup (one-time)
make venv

# Run commands
make scan                                    # Scan for devices
make pair DEVICE="WowME ID217G"             # Pair with device
make all DEVICE="WowME ID217G"              # Full setup
```

## Architecture

### Core Components

- **`veryfit_client.py`** - Main Python BLE client (574 lines)
  - `VeryFitProtocol` - Protocol encoding/decoding
  - `VeryFitDevice` - BLE device communication
  - CLI interface with async commands

### BLE Protocol

- **Service UUID**: `00001101-0000-1000-8000-00805F9B34FB`
- **Write Characteristic**: `00000af4-0000-1000-8000-00805f9b34fb`
- **Notify Characteristics**: `00000af0-0000-1000-8000-00805f9b34fb`, `00000af1`, `00000af2`, `00000af6`, `00000af7`
- **CCCD**: `00002902-0000-1000-8000-00805f9b34fb`

### Command Codes

| Code | Command | Purpose |
|------|---------|---------|
| 9216 | `CMD_BIND` | Bind/Pair device |
| 5514 | `CMD_SYSTEM_TIME` | Time sync |
| 1000 | `CMD_USER_INFO` | User profile |
| 5000 | `CMD_GOAL` | Daily goals |
| 1001 | `CMD_HEALTH_DATA` | Health data sync |
| 1002 | `CMD_CONFIG_INFO` | Config info |

## Development Guidelines

### Adding New Commands

1. Add command code to `CMD_*` constants in `veryfit_client.py`
2. Create encoding method in `VeryFitProtocol` class
3. Add wrapper method in `VeryFitDevice` class
4. Add CLI handler in `main()` function
5. Add Makefile target if needed

### Protocol Encoding

- Format: `[cmd_code:4 bytes LE][data...]`
- Use `VeryFitProtocol.make_command(cmd_code, data)` for wrapping
- Payloads use `struct.pack()` with little-endian (`<`) format

### Bind/Pair Flow

```python
# Phase 1: BindPara
bind_para = VeryFitProtocol.encode_bind_request()
resp = await device.write_command(CMD_BIND, bind_para)

# Phase 2: BindAuth (if auth_code_required)
bind_auth = VeryFitProtocol.encode_bind_auth(auth_code)
resp = await device.write_command(CMD_BIND, bind_auth)
```

### Notification Handling

Notifications are received via callback and queued:

```python
def notification_handler(characteristic, data):
    await device._response_queue.put(data)

await device.enable_notifications(NOTIFY_CHAR_UUID, notification_handler)
```

## Testing

```bash
make lint        # Run ruff linter
make run args="scan"  # Test scan
```

## Dependencies

- **bleak>=0.20.0** - BLE client library (Linux D-Bus backend)
- **Python 3.10+** - Required for typing features

## Known Issues

- Native library encryption not fully reversed (basic commands work)
- Health data parsing not implemented
- Notification callback uses deprecated `asyncio.get_event_loop()` - consider `asyncio.get_running_loop()`

## Files

| File | Purpose |
|------|---------|
| `veryfit_client.py` | Main Python client |
| `requirements.txt` | Python dependencies |
| `Makefile` | Build/run commands |
| `README.md` | Project documentation |
| `AGENTS.md` | Agent instructions |
| `.venv/` | Virtual environment |
| `VeryFit_2.8.10_APKPure.apk` | Source APK (173MB) |
| `decompiled/` | Decompiled Java source (29,370 classes) |
| `extracted/lib/` | Native libraries (.so files) |

## Reverse Engineering Artifacts

### Decompiled Source

Located in `decompiled/sources/`:
- `com/ido/ble/BLEManager.java` - Main BLE manager (74KB)
- `com/ido/ble/bluetooth/e/f.java` - BLE UUID definitions
- `com/veryfit/multi/nativeprotocol/b.java` - Command codes
- `com/ido/ble/protocol/model/*.java` - Protocol model classes

### Native Libraries

Located in `extracted/lib/arm64-v8a/`:
- `libVeryFitMulti.so` - Native protocol library
- `libprotocol.so` - Protocol handling
- `libEncryptorP.so` - Encryption
- `libAesJni.so` - AES JNI bindings

## Troubleshooting

### BLE Connection Issues

1. Ensure Bluetooth is enabled: `bluetoothctl`
2. Check device is in pairing mode
3. Verify device name/address matches
4. Run `make scan` to discover devices

### Lint/Build Errors

```bash
make lint    # Check for lint errors
make clean   # Clean and rebuild
```

### Python Version

Project requires Python 3.10+. Check with:
```bash
python3 --version
```
