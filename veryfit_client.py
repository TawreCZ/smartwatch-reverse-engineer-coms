#!/usr/bin/env python3
"""
VeryFit / WowME ID217G Sport Black - BLE Protocol Client

Reverse engineered from VeryFit APK 2.8.10
BLE Protocol implementation for connecting to smartwatch devices.

BLE UUIDs discovered from APK:
- Service:        00001101-0000-1000-8000-00805F9B34FB
- Write Char:     00000aF4-0000-1000-8000-00805f9b34fb
- Notify Chars:   00000aF0-0000-1000-8000-00805f9b34fb, 00000aF1-..., 00000aF2-...
- CCCD:           00002902-0000-1000-8000-00805f9b34fb
- DFU:            0000FD50-0000-1000-8000-00805f9b34fb
- Other:          00000aF6-..., 00000aF7-..., 0000fe59-...

Protocol:
- Data is JSON-serialized, then encrypted using native library (AES-based)
- Commands use numeric codes (e.g., 9216 for time sync, 1000 for user info)
- Bind/Pair: Two-phase (BindPara -> BindAuth)
"""

import asyncio
import struct
import logging
from datetime import datetime
from typing import Optional, Callable

from bleak import BleakScanner, BleakClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# === BLE UUIDs from the APK ===
SERVICE_UUID = "00001101-0000-1000-8000-00805F9B34FB"
WRITE_CHAR_UUID = "00000af4-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_UUID = "00000af0-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_2_UUID = "00000af1-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_3_UUID = "00000af2-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_4_UUID = "00000af6-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_5_UUID = "00000af7-0000-1000-8000-00805f9b34fb"
CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"
DFU_SERVICE_UUID = "0000fd50-0000-1000-8000-00805f9b34fb"
NORDIC_SERVICE_UUID = "0000fe59-0000-1000-8000-00805f9b34fb"

# === Protocol Command Codes from APK (com.veryfit.multi.nativeprotocol.b) ===
CMD_BIND = 9216          # X5 - Bind/Pair command
CMD_USER_INFO = 1000     # r3 - User info
CMD_SYSTEM_TIME = 5514   # H4 - System time
CMD_GOAL = 5000          # B3 - Daily goal (steps/calories)
CMD_ALARM = 5001         # C3 - Alarm
CMD_HEALTH_DATA = 1001   # s4 - Health data sync
CMD_CONFIG_INFO = 1002   # t4 - Config info
CMD_NOT_DISTURB = 186    # C0 - Do not disturb
CMD_HEART_RATE_INTERVAL = 553  # m2 - Heart rate interval
CMD_HEART_RATE_MODE = 561  # u2 - Heart rate measure mode
CMD_ACTIVITY_SWITCH = 167  # q1 - Activity display switch
CMD_WEATHER = 650        # n3 - Weather
CMD_MESSAGE_NOTIFY = 5006  # F3 - Message notification
CMD_PHONE_CONTACTS = 620 # d3 - Phone contacts
CMD_BLOOD_PRESSURE = 126 # W - Blood pressure
CMD_SPO2 = 604           # Q2 - Blood oxygen
CMD_SLEEP_MONITOR = 303  # V0 - Sleep monitoring
CMD_BODY_POWER = 192     # H0 - Body power/composition

# Bind/Pair responses
BIND_SUCCESS = 0
BIND_FAIL = 1
BIND_AUTH_CODE_LOST = 2

# Auth types
AUTH_TYPE_CLEAN = 1
OS_TYPE_ANDROID = 2
OS_VERSION = 2


class VeryFitProtocol:
    """Handles VeryFit protocol data formatting."""

    @staticmethod
    def encode_system_time(year: int, month: int, day: int,
                           hour: int, minute: int, second: int,
                           timezone_offset: int = 0, week: int = 0) -> bytes:
        """Encode SystemTime packet for time sync.
        
        From APK: SystemTime class with fields:
        year, month, day, hour, minute, second, week, time_zone
        """
        # Protocol format: [cmd:4][data_len:2][payload...]
        payload = struct.pack('<BBBBBBhH',
                              year, month, day, hour, minute, second,
                              timezone_offset, week)
        # Add year as 2-byte at beginning
        payload = struct.pack('>H', year) + payload
        return payload

    @staticmethod
    def encode_user_info(gender: int, weight_kg: float, height_cm: int,
                         birth_year: int, birth_month: int, birth_day: int) -> bytes:
        """Encode UserInfo packet.
        
        From APK: UserInfo class with fields:
        gender (0=MALE, 1=FEMALE), weight (kg*100), height (cm),
        birth year, month, day
        """
        weight_x100 = int(weight_kg * 100)
        payload = struct.pack('<HBBBBB',
                              weight_x100, height_cm, gender,
                              birth_year, birth_month, birth_day)
        return payload

    @staticmethod
    def encode_bind_request(is_clean: int = AUTH_TYPE_CLEAN) -> bytes:
        """Encode BindPara for initial pairing.
        
        From APK: BindPara class:
        os_type=2 (Android), os_version=2, is_clean_data=1, bind_version=1
        """
        payload = struct.pack('<BBBB',
                              OS_TYPE_ANDROID, OS_VERSION, is_clean, 1)
        return payload

    @staticmethod
    def encode_bind_auth(auth_code: list = None) -> bytes:
        """Encode BindAuth for authentication phase.
        
        From APK: BindAuth class:
        os_type=1, os_version=2, is_clean_data=1, auth_code, auth_length
        """
        if auth_code is None:
            auth_code = [0, 0, 0, 0, 0, 0]
        auth_length = len(auth_code)
        payload = struct.pack('<Ii', auth_length, AUTH_TYPE_CLEAN)
        payload += struct.pack(f'<{auth_length}I', *auth_code)
        return payload

    @staticmethod
    def make_command(cmd_code: int, data: bytes) -> bytes:
        """Wrap data with command code header.
        
        Format: [cmd_code:4 little-endian][data]
        """
        return struct.pack('<I', cmd_code) + data


class VeryFitDevice:
    """Client for VeryFit/WowME smartwatch BLE protocol."""

    def __init__(self, client: BleakClient):
        self.client = client
        self.characteristics: dict = {}
        self._response_queue: asyncio.Queue = asyncio.Queue()
        self._connected = False

    async def connect(self) -> bool:
        """Connect to the device and discover services."""
        try:
            await self.client.connect()
            logger.info("Connected to device")

            # Discover services
            services = await self.client.get_services()
            logger.info(f"Discovered {len(services)} services")

            # Map characteristics
            for service in services:
                self.characteristics[service.uuid] = service.characteristics
                for char in service.characteristics:
                    logger.debug(f"  Char {char.uuid}: props={char.properties}")

            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the device."""
        if self.client.is_connected:
            await self.client.disconnect()
            logger.info("Disconnected")

    async def enable_notifications(self, char_uuid: str,
                                    callback: Optional[Callable] = None):
        """Enable notifications on a characteristic."""
        # Find the characteristic
        char = None
        for service_uuid, chars in self.characteristics.items():
            for c in chars:
                if c.uuid == char_uuid:
                    char = c
                    break
            if char:
                break

        if not char:
            logger.warning(f"Characteristic not found: {char_uuid}")
            return

        if 'notify' not in char.properties:
            logger.warning(f"Characteristic doesn't support notify: {char_uuid}")
            return

        # CCCD value to enable notifications (0x01)
        cccd_enable = b'\x01\x00'

        try:
            await self.client.write_gatt_char(CCCD_UUID, cccd_enable)
            logger.info(f"Notifications enabled for {char_uuid}")

            if callback:
                await self.client.start_notify(char_uuid, callback)
        except Exception as e:
            logger.error(f"Failed to enable notifications: {e}")

    async def write_command(self, cmd_code: int, data: bytes,
                            wait_response: bool = True,
                            response_timeout: float = 5.0) -> Optional[bytes]:
        """Send a BLE command to the device.
        
        Args:
            cmd_code: Protocol command code
            data: Payload data
            wait_response: Whether to wait for device response
            response_timeout: Timeout in seconds for response
        """
        # Wrap with command code
        packet = VeryFitProtocol.make_command(cmd_code, data)
        logger.debug(f"Sending command {cmd_code}, {len(packet)} bytes: {packet.hex()}")

        try:
            await self.client.write_gatt_char(WRITE_CHAR_UUID, packet)

            if wait_response:
                try:
                    response = await asyncio.wait_for(
                        self._response_queue.get(),
                        timeout=response_timeout
                    )
                    return response
                except asyncio.TimeoutError:
                    logger.warning(f"No response received for command {cmd_code}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Write failed: {e}")
            return None

    async def bind(self, auth_code: list = None) -> bool:
        """Perform bind/pair with the device.
        
        Two-phase process:
        1. Send BindPara
        2. Send BindAuth (if required)
        """
        logger.info("Starting bind/pair process...")

        # Phase 1: BindPara
        bind_para = VeryFitProtocol.encode_bind_request()
        resp = await self.write_command(CMD_BIND, bind_para, wait_response=True)

        if resp:
            logger.info(f"BindPara response: {resp.hex()}")
            # Check bind response code
            if len(resp) >= 1:
                bind_ret = resp[0]
                if bind_ret == BIND_SUCCESS:
                    logger.info("Bind successful!")
                    return True
                elif bind_ret == BIND_AUTH_CODE_LOST:
                    logger.info("Auth code required, proceeding to phase 2")
                else:
                    logger.info(f"Bind response code: {bind_ret}")

        # Phase 2: BindAuth
        if auth_code:
            bind_auth = VeryFitProtocol.encode_bind_auth(auth_code)
            resp = await self.write_command(CMD_BIND, bind_auth, wait_response=True)
            if resp:
                logger.info(f"BindAuth response: {resp.hex()}")
                return True

        logger.info("Bind process completed")
        return True

    async def set_time(self, timezone_offset_hours: int = 0) -> bool:
        """Set the device time to current time.
        
        Args:
            timezone_offset_hours: UTC offset in hours (e.g., +1 for CET)
        """
        logger.info("Setting device time...")

        now = datetime.now()

        # Calculate week day (1=Monday, 7=Sunday)
        week_day = now.isoweekday()

        time_data = VeryFitProtocol.encode_system_time(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            minute=now.minute,
            second=now.second,
            timezone_offset=timezone_offset_hours,
            week=week_day
        )

        resp = await self.write_command(CMD_SYSTEM_TIME, time_data)
        if resp:
            logger.info(f"Time set response: {resp.hex()}")
        else:
            logger.info("Time set (no response expected)")

        return True

    async def set_user_info(self, gender: int, weight_kg: float,
                           height_cm: int, birth_year: int,
                           birth_month: int, birth_day: int) -> bool:
        """Set user profile information.
        
        Args:
            gender: 0=MALE, 1=FEMALE
            weight_kg: Weight in kilograms
            height_cm: Height in centimeters
            birth_year: Birth year
            birth_month: Birth month
            birth_day: Birth day
        """
        logger.info("Setting user info...")

        user_data = VeryFitProtocol.encode_user_info(
            gender=gender,
            weight_kg=weight_kg,
            height_cm=height_cm,
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day
        )

        resp = await self.write_command(CMD_USER_INFO, user_data)
        if resp:
            logger.info(f"User info response: {resp.hex()}")

        return True

    async def set_daily_goal(self, steps: int = 10000,
                             calories: int = 2000,
                             distance_m: int = 8000) -> bool:
        """Set daily activity goals.
        
        Args:
            steps: Target steps per day
            calories: Target calories per day
            distance_m: Target distance in meters
        """
        logger.info(f"Setting daily goal: {steps} steps, {calories} cal")

        # Goal format from APK: Goal class
        goal_data = struct.pack('<III', steps, calories, distance_m)

        resp = await self.write_command(CMD_GOAL, goal_data)
        if resp:
            logger.info(f"Goal response: {resp.hex()}")

        return True

    async def request_health_data(self) -> bool:
        """Request health data sync from device."""
        logger.info("Requesting health data sync...")

        # StartSyncHealthData command
        await self.write_command(CMD_HEALTH_DATA, b'', wait_response=False)

        # The device will send data via notification characteristic
        return True

    async def request_config_info(self) -> bool:
        """Request configuration info from device."""
        logger.info("Requesting config info...")

        await self.write_command(CMD_CONFIG_INFO, b'', wait_response=False)
        return True

    async def get_device_info(self) -> Optional[dict]:
        """Get basic device information."""
        logger.info("Getting device info...")

        # Try to read battery level from standard BLE service
        try:
            battery = await self.client.read_gatt_char("00002a19-0000-1000-8000-00805f9b34fb")
            logger.info(f"Battery level: {battery[0]}%")
            return {"battery": battery[0]}
        except Exception as e:
            logger.debug(f"Could not read battery: {e}")

        return None

    async def list_characteristics(self):
        """List all available characteristics."""
        for service_uuid, chars in self.characteristics.items():
            logger.info(f"Service: {service_uuid}")
            for char in chars:
                logger.info(f"  - {char.uuid}: {char.properties}")


async def scan_devices(timeout: float = 10.0, show_adv: bool = False) -> list:
    """Scan for nearby BLE devices."""
    logger.info(f"Scanning for BLE devices ({timeout}s)...")
    logger.info(f"BLE backend: {BleakScanner.backend_id}")
    devices = []

    def detection_callback(scan_device, advertisement_data):
        devices.append({
            'device': scan_device,
            'adv_data': advertisement_data
        })
        name = scan_device.name or "Unknown"
        addr = scan_device.address
        rssi = advertisement_data.rssi if advertisement_data else "N/A"
        logger.info(f"  Found: {name} ({addr}) RSSI={rssi}")
        if show_adv:
            logger.debug(f"    Adv data: {advertisement_data}")

    scanner = BleakScanner(detection_callback=detection_callback)
    logger.info("Starting BLE scan...")
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    logger.info(f"Scan complete. Found {len(devices)} device(s)")

    return devices


async def main():
    """Main entry point demonstrating usage."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python veryfit_client.py <command> [args]")
        print()
        print("Commands:")
        print("  scan              - Scan for nearby BLE devices")
        print("  scan --debug      - Scan with verbose debug output")
        print("  connect <addr>    - Connect to device by address or name")
        print("  pair <addr>       - Pair/bind with device")
        print("  settime <addr>    - Set device time")
        print("  userinfo <addr>   - Set user info")
        print("  goal <addr>       - Set daily goals")
        print("  data <addr>       - Request health data")
        print("  all <addr>        - Full setup: pair + time + userinfo + goal")
        print()
        print("Examples:")
        print("  python veryfit_client.py scan")
        print("  python veryfit_client.py pair 'WowME ID217G'")
        print("  python veryfit_client.py settime 'WowME ID217G'")
        print("  python veryfit_client.py all 'WowME ID217G'")
        return

    command = sys.argv[1]

    if command == "scan":
        devices = await scan_devices()
        if devices:
            print(f"\nFound {len(devices)} device(s):")
            for d in devices:
                name = d['device'].name or "Unknown"
                addr = d['device'].address
                print(f"  {name} ({addr})")
        else:
            print("No devices found")

    elif command in ("connect", "pair", "settime", "userinfo", "goal", "data", "all"):
        if len(sys.argv) < 3:
            print("Error: Please specify device address or name")
            print("Use 'scan' command first to find devices")
            return

        device_name = sys.argv[2]

        # Scan first to get the device
        devices = await scan_devices(timeout=5.0)
        target_device = None

        for d in devices:
            name = d['device'].name or ""
            addr = d['device'].address
            if device_name.lower() in name.lower() or device_name == addr:
                target_device = d['device']
                break

        if not target_device:
            # Try using the name as address
            target_device = type('Device', (), {
                'name': device_name,
                'address': device_name
            })()

        if not target_device:
            print(f"Device '{device_name}' not found during scan")
            return

        print(f"\nConnecting to: {target_device.name} ({target_device.address})")

        # Extract address as string to avoid passing BleakDevice object
        device_addr = str(target_device.address)
        print(f"  Using address: {device_addr}")
        async with BleakClient(device_addr, timeout=30.0) as client:

            device = VeryFitDevice(client)

            # Set up notification callback
            def notification_handler(char, data):
                logger.info(f"Notification on {char}: {data.hex()}")
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.get_event_loop()
                loop.create_task(
                    device._response_queue.put(data)
                )

            connected = await device.connect()
            if not connected:
                print("Failed to connect")
                return

            # List discovered characteristics
            logger.info("Discovered characteristics:")
            for service_uuid, chars in device.characteristics.items():
                for char in chars:
                    logger.info(f"  {char.uuid}: {char.properties}")

            # Enable notifications on all possible notify characteristics
            for char_uuid in [NOTIFY_CHAR_UUID, NOTIFY_CHAR_2_UUID,
                              NOTIFY_CHAR_3_UUID, NOTIFY_CHAR_4_UUID,
                              NOTIFY_CHAR_5_UUID]:
                await device.enable_notifications(char_uuid, notification_handler)

            if command == "connect":
                print("Connected successfully!")

            elif command == "pair":
                await device.bind()
                print("Pairing completed!")

            elif command == "settime":
                await device.set_time()
                print("Time set successfully!")

            elif command == "userinfo":
                # Default user info - customize as needed
                # gender=0 (male), weight=70kg, height=175cm,
                # birth=1990-01-01
                await device.set_user_info(
                    gender=0,
                    weight_kg=70.0,
                    height_cm=175,
                    birth_year=1990,
                    birth_month=1,
                    birth_day=1
                )
                print("User info set!")

            elif command == "goal":
                await device.set_daily_goal(steps=10000, calories=2000)
                print("Daily goal set!")

            elif command == "data":
                await device.request_health_data()
                print("Health data request sent. Watch device for responses...")
                await asyncio.sleep(5)

            elif command == "all":
                print("\n--- Full Setup ---")
                print("1. Pairing...")
                await device.bind()
                print("2. Setting time...")
                await device.set_time()
                print("3. Setting user info...")
                await device.set_user_info(
                    gender=0, weight_kg=70.0, height_cm=175,
                    birth_year=1990, birth_month=1, birth_day=1
                )
                print("4. Setting daily goal...")
                await device.set_daily_goal()
                print("\nFull setup complete!")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
