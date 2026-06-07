#!/usr/bin/env python3
"""Direct connection diagnostic."""

import asyncio
import sys
from bleak import BleakClient

async def try_direct_connect(address, timeout=10.0):
    """Try to connect directly without scanning."""
    print(f"\n=== Direct Connection Test ===")
    print(f"Address: {address}\n")
    
    try:
        print("Attempting to connect...")
        async with BleakClient(address, timeout=timeout) as client:
            if client.is_connected:
                print("✓ CONNECTED!")
                services = await client.get_services()
                print(f"\nServices found: {len(services)}")
                for svc in services:
                    print(f"  - {svc.uuid}")
                return True
            else:
                print("✗ Connected but not ready")
                return False
    except Exception as e:
        print(f"✗ Connection failed: {type(e).__name__}")
        print(f"   {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python direct_connect.py <MAC_ADDRESS>")
        print("\nPut your watch in pairing mode first!")
        print("Hold side button 10+ seconds until 'Pairing' appears")
        sys.exit(1)
    
    address = sys.argv[1]
    asyncio.run(try_direct_connect(address))

if __name__ == "__main__":
    main()
