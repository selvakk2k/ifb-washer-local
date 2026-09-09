import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import (
    build_program_selection,
    build_user_option_command,
)
from ifb_washer_local.const import (
    HIL_OPTION_SPIN,
    HIL_OPTION_TEMP,
)

async def probe():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # First set Mix / Daily (code 13)
        print("Selecting Mix / Daily...")
        await client.select_program(13)
        await asyncio.sleep(1.0)
        st = await client.get_state()
        print(f"Mix / Daily default -> Spin: {st.spin_speed_name} (code {st.spin_speed_code}), Temp: {st.temperature_name} (code {st.temperature_code})")
        print(f"Raw[7..11]: {[hex(b) for b in bytes.fromhex(st.raw_hex)[7:12]]}")

        # Test HIL_OPTION_SPIN values 0..7
        for val in [1, 2, 3, 4, 5, 6, 7]:
            pkt = build_user_option_command(HIL_OPTION_SPIN, val)
            await client._send_raw_command(pkt)
            await asyncio.sleep(0.6)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"HIL_SPIN val={val} -> Spin: {st.spin_speed_name} (code={st.spin_speed_code}), Raw[8]={hex(raw[8])}, Raw[9]={hex(raw[9])}, Raw[10]={hex(raw[10])}")

        # Test HIL_OPTION_TEMP values 1..7
        for val in [1, 2, 3, 4, 5, 6, 7]:
            pkt = build_user_option_command(HIL_OPTION_TEMP, val)
            await client._send_raw_command(pkt)
            await asyncio.sleep(0.6)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"HIL_TEMP val={val} -> Temp: {st.temperature_name} (code={st.temperature_code}), Raw[8]={hex(raw[8])}, Raw[9]={hex(raw[9])}, Raw[10]={hex(raw[10])}")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(probe())
