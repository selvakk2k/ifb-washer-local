import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import compute_checksums, FRAME_HEADER, CMD_TYPE_USER_OPTION

async def probe_spin_encodings():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # Reset Cotton (12)
        await client.select_program(12)
        await asyncio.sleep(1.0)
        
        # Test 1: RPM / 100 values (4, 6, 8, 10, 12, 14)
        print("--- Testing RPM / 100 on HIL 5 ---")
        for val in [4, 6, 8, 10, 12, 14]:
            pkt = [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x01, 5, val, 0x00, 0x00, 0x00]
            chk1, chk2 = compute_checksums(pkt[:-2])
            pkt[-2] = chk1
            pkt[-1] = chk2
            await client._send_raw_command(bytes(pkt))
            await asyncio.sleep(0.4)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Val {val} -> Spin: {st.spin_speed_name} (Raw[8]={hex(raw[8])})")

        # Reset Cotton
        await client.select_program(12)
        await asyncio.sleep(1.0)

        # Test 2: Sequential indices 0..6
        print("\n--- Testing Sequential indices on HIL 5 ---")
        for val in [0, 1, 2, 3, 4, 5, 6]:
            pkt = [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x01, 5, val, 0x00, 0x00, 0x00]
            chk1, chk2 = compute_checksums(pkt[:-2])
            pkt[-2] = chk1
            pkt[-1] = chk2
            await client._send_raw_command(bytes(pkt))
            await asyncio.sleep(0.4)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Index {val} -> Spin: {st.spin_speed_name} (Raw[8]={hex(raw[8])})")

        # Reset Cotton
        await client.select_program(12)
        await asyncio.sleep(1.0)

        # Test 3: 16-bit big-endian RPM on HIL 5: e.g. 1200 = 0x04B0 -> [5, 0x04, 0xB0]
        print("\n--- Testing 16-bit RPM on HIL 5 ---")
        for rpm in [400, 600, 800, 1000, 1200, 1400]:
            pkt = [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x01, 5, (rpm >> 8) & 0xFF, rpm & 0xFF, 0x00, 0x00]
            chk1, chk2 = compute_checksums(pkt[:-2])
            pkt[-2] = chk1
            pkt[-1] = chk2
            await client._send_raw_command(bytes(pkt))
            await asyncio.sleep(0.4)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"RPM {rpm} (16-bit) -> Spin: {st.spin_speed_name} (Raw[8]={hex(raw[8])})")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(probe_spin_encodings())
