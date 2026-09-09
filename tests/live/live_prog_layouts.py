import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import compute_checksums, FRAME_HEADER, CMD_TYPE_PROGRAM_SELECT

async def test_program_select():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # Let's test various candidate packet layouts for Program 13 (Mix/Daily), Spin 7 (1200 RPM), Temp 4 (40°C)
        # Layout 1: [63, 13, 03, 00, 00, 13, 00, 07, 00, 04, 00, 00, 00, 00, 00, 00, 00, 00, 00, chk1, chk2]
        # Layout 2: [63, 13, 03, 00, 00, 13, 07, 04, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00, chk1, chk2]
        # Layout 3: [63, 13, 03, 00, 13, 07, 04, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00, chk1, chk2]

        tests = [
            ("Layout 1 (zeros spaced: 5=prog, 7=spin, 9=temp)", [FRAME_HEADER, 0x13, CMD_TYPE_PROGRAM_SELECT, 0x00, 0x00, 13, 0x00, 7, 0x00, 4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            ("Layout 2 (5=prog, 6=spin, 7=temp)", [FRAME_HEADER, 0x13, CMD_TYPE_PROGRAM_SELECT, 0x00, 0x00, 13, 7, 4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            ("Layout 3 (4=prog, 5=spin, 6=temp)", [FRAME_HEADER, 0x13, CMD_TYPE_PROGRAM_SELECT, 0x00, 13, 7, 4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            ("Layout 4 (5=prog, 6=0, 7=temp, 8=0, 9=spin)", [FRAME_HEADER, 0x13, CMD_TYPE_PROGRAM_SELECT, 0x00, 0x00, 13, 0x00, 4, 0x00, 7, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ]

        for name, pkt in tests:
            chk1, chk2 = compute_checksums(pkt[:-2])
            pkt[-2] = chk1
            pkt[-1] = chk2
            pkt_bytes = bytes(pkt)
            print(f"\n--- Testing {name} ---")
            print(f"Packet: {pkt_bytes.hex()}")
            await client._send_raw_command(pkt_bytes)
            await asyncio.sleep(1.0)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Result -> Prog: {st.program_code} ({st.program_name}), Spin: {st.spin_speed_name} (Raw[8]={hex(raw[8])}), Temp: {st.temperature_name} (Raw[10]={hex(raw[10])})")
            print(f"Raw[5..14]: {[hex(b) for b in raw[5:15]]}")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_program_select())
