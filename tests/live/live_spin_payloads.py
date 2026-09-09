import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import compute_checksums, FRAME_HEADER, CMD_TYPE_USER_OPTION

async def test_spin_payload_positions():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # We want to set 1200 RPM (code 7) or 1000 RPM (code 6)
        candidates = [
            ("HIL 5: [0x01, 5, 7, 0]", [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x01, 5, 7, 0, 0, 0]),
            ("HIL 5: [0x01, 5, 0, 7]", [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x01, 5, 0, 7, 0, 0]),
            ("HIL 5: [0x02, 5, 7, 0]", [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x02, 5, 7, 0, 0, 0]),
            ("HIL 5: [0x02, 5, 0, 7]", [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x02, 5, 0, 7, 0, 0]),
            ("HIL 5: [0x00, 5, 7, 0]", [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x00, 5, 7, 0, 0, 0]),
            ("HIL 5: [0x00, 5, 0, 7]", [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x00, 5, 0, 7, 0, 0]),
            ("HIL 5: 16-bit [0x01, 5, 0x04, 0xb0]", [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x01, 5, 0x04, 0xb0, 0, 0]),
            ("HIL 5: 16-bit [0x02, 5, 0x04, 0xb0]", [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x02, 5, 0x04, 0xb0, 0, 0]),
        ]

        for name, pkt in candidates:
            chk1, chk2 = compute_checksums(pkt[:-2])
            pkt[-2] = chk1
            pkt[-1] = chk2
            print(f"\n--- Testing {name} ---")
            print(f"Packet: {bytes(pkt).hex()}")
            await client._send_raw_command(bytes(pkt))
            await asyncio.sleep(0.5)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Result -> Spin: {st.spin_speed_name} (code={st.spin_speed_code}, Raw[8]={hex(raw[8])})")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_spin_payload_positions())
