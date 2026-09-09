import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import build_user_option_command

async def test_all_hils():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # Reset to Mix/Daily
        await client.select_program(13)
        await asyncio.sleep(1.0)
        
        # Test HIL IDs 1..25 with value 6 (or 1000 RPM) or 7 (1200 RPM) or 4 (800 RPM)
        for hil_id in range(1, 26):
            # Send value 6 or 4
            pkt = build_user_option_command(hil_id, 6)
            await client._send_raw_command(pkt)
            await asyncio.sleep(0.4)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"HIL ID {hil_id:2d} (val=6) -> Spin: {st.spin_speed_name} (Raw[8]={hex(raw[8])}), Temp: {st.temperature_name} (Raw[10]={hex(raw[10])}), Raw[7..12]: {[hex(b) for b in raw[7:13]]}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_all_hils())
