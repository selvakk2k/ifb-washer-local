import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import build_user_option_command, HIL_OPTION_SPIN

async def probe_spin():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # Reset to Mix / Daily
        await client.select_program(13)
        await asyncio.sleep(1.0)
        
        # Test Option ID 5 with values: 0, 1, 2, 4, 6, 7, 8, 10, 12, 14, 400, 600, 800, 1000, 1200, 1400
        test_values = [0, 1, 2, 4, 6, 7, 8, 10, 12, 14, 0x01, 0x02, 0x04, 0x06, 0x07, 0x08]
        for v in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14]:
            pkt = build_user_option_command(5, v)
            await client._send_raw_command(pkt)
            await asyncio.sleep(0.5)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"HIL 5 with val={v:2d} -> Spin: {st.spin_speed_name} (Raw[8]={hex(raw[8])})")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(probe_spin())
