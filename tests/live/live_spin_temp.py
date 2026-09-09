import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import build_user_option_command
from ifb_washer_local.const import HIL_OPTION_SPIN, HIL_OPTION_TEMP

async def test_cotton_and_mix():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # 1. Select Cotton (Program 12)
        print("=== SELECTING COTTON (12) ===")
        await client.select_program(12)
        await asyncio.sleep(1.0)
        st = await client.get_state()
        print(f"Cotton default -> Program: {st.program_name} (code {st.program_code}), Spin: {st.spin_speed_name} (code {st.spin_speed_code}), Temp: {st.temperature_name} (code {st.temperature_code})")
        print(f"Raw[7..12]: {[hex(b) for b in bytes.fromhex(st.raw_hex)[7:13]]}")

        # Test Spin codes 0, 1 (400), 2 (600), 4 (800), 6 (1000), 7 (1200), 8 (1400) on Cotton via HIL_OPTION_SPIN (5)
        for spin_code, rpm in [(0, "No Spin"), (1, "400 RPM"), (2, "600 RPM"), (4, "800 RPM"), (6, "1000 RPM"), (7, "1200 RPM"), (8, "1400 RPM")]:
            pkt = build_user_option_command(HIL_OPTION_SPIN, spin_code)
            await client._send_raw_command(pkt)
            await asyncio.sleep(0.5)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Set Spin Code {spin_code} ({rpm}) -> Reported Spin: {st.spin_speed_name} (Raw[8]={hex(raw[8])})")

        # 2. Test Temp codes on Cotton via HIL_OPTION_TEMP (3)
        # Codes: 2 (Cold), 7 (20°C), 3 (30°C), 4 (40°C), 5 (60°C), 6 (95°C)
        print("\n=== TESTING TEMP ON COTTON ===")
        for temp_code, label in [(2, "Cold"), (7, "20°C"), (3, "30°C"), (4, "40°C"), (5, "60°C"), (6, "95°C")]:
            pkt = build_user_option_command(HIL_OPTION_TEMP, temp_code)
            await client._send_raw_command(pkt)
            await asyncio.sleep(0.5)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Set Temp Code {temp_code} ({label}) -> Reported Temp: {st.temperature_name} (Raw[10]={hex(raw[10])})")

        # 3. Select Mix / Daily (Program 13)
        print("\n=== SELECTING MIX / DAILY (13) ===")
        await client.select_program(13)
        await asyncio.sleep(1.0)
        st = await client.get_state()
        print(f"Mix / Daily default -> Program: {st.program_name} (code {st.program_code}), Spin: {st.spin_speed_name}, Temp: {st.temperature_name}")

        for spin_code, rpm in [(0, "No Spin"), (1, "400 RPM"), (2, "600 RPM"), (4, "800 RPM"), (6, "1000 RPM"), (7, "1200 RPM")]:
            pkt = build_user_option_command(HIL_OPTION_SPIN, spin_code)
            await client._send_raw_command(pkt)
            await asyncio.sleep(0.5)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Mix/Daily Set Spin Code {spin_code} ({rpm}) -> Reported Spin: {st.spin_speed_name} (Raw[8]={hex(raw[8])})")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_cotton_and_mix())
