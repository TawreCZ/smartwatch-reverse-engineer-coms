#!/usr/bin/env python3
"""BLE Diagnostics Tool"""

import subprocess
import sys
import asyncio
from bleak import BleakScanner

def run_cmd(cmd):
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error: {e}"

def check_bt_status():
    """Check Bluetooth status."""
    print("\n=== Bluetooth Status ===")
    print(run_cmd("bluetoothctl show | grep -E 'Powered|Name|Version|Class'"))
    print("\nPaired Devices:")
    print(run_cmd("bluetoothctl paired-devices"))

def check_bt_adapter():
    """Check Bluetooth adapter details."""
    print("\n=== Bluetooth Adapter ===")
    print(run_cmd("btmgmt info 2>/dev/null || echo 'btmgmt not available'"))

def check_usb_adapters():
    """Check USB Bluetooth adapters."""
    print("\n=== USB Adapters ===")
    usb = run_cmd("lsusb | grep -i blue")
    if usb:
        print(usb)
    else:
        print("No USB Bluetooth adapters found (using built-in)")

async def scan_ble(timeout=15):
    """Scan for BLE devices."""
    print(f"\n=== BLE Scan ({timeout}s) ===")
    devices = []

    def callback(device, adv_data):
        name = device.name or "Unknown"
        addr = device.address
        rssi = adv_data.rssi if adv_data else "N/A"
        devices.append((name, addr, rssi))
        print(f"  Found: {name} ({addr}) RSSI={rssi}")

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()

    if not devices:
        print("  No BLE devices found!")

    return devices

def check_watch_requirements():
    """Print watch pairing requirements."""
    print("\n=== Watch Pairing Checklist ===")
    print("1. ✓ Watch is powered ON")
    print("2. ☐ Watch is in PAIRING MODE (hold button 10+ seconds)")
    print("3. ☐ Watch is NOT already paired with phone (forget on phone)")
    print("4. ☐ Watch is within 1-2 meters of laptop")
    print("5. ☐ No physical obstructions between watch and laptop")
    print("\nOn phone:")
    print("  - Go to Bluetooth settings")
    print("  - Find 'WowME ID217G' or similar")
    print("  - Tap 'Forget' or 'Unpair'")
    print("\nOn watch:")
    print("  - Hold side button 10+ seconds until 'Pairing' shows")
    print("  - Or factory reset if available")

async def main():
    check_bt_status()
    check_bt_adapter()
    check_usb_adapters()
    devices = await scan_ble()

    if not devices:
        check_watch_requirements()

if __name__ == "__main__":
    asyncio.run(main())
