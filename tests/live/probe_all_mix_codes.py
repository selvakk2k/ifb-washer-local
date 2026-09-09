import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import compute_checksums, FRAME_HEADER, CMD_TYPE_USER_OPTION

async def test_all_mix_codes():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        print("=== PROBING ALL OPTION 5 VALUES ON MIX / DAILY ===")
        
        # Test values 0 to 20 on Mix / Daily
        for val in range(21):
            # Select Mix / Daily first to ensure clean baseline
            await client.select_program(13)
            await asyncio.sleep(0.6)
            
            # Send Option 5 with val
            pkt = [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x01, 0x05, 0x00, val, 0x00, 0x00]
            chk1, chk2 = compute_checksums(pkt[:-2])
            pkt[-2] = chk1
            pkt[-1] = chk2
            
            await client._send_raw_command(bytes(pkt))
            await asyncio.sleep(0.5)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Val {val:2d} -> Spin: {st.spin_speed_name:10s} (Raw[8]={hex(raw[8])}), Rinse Hold: {st.rinse_hold!s:5s} (Raw[11]={hex(raw[11])})")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_all_mix_codes())
