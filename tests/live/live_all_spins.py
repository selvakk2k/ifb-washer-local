import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import compute_checksums, FRAME_HEADER, CMD_TYPE_USER_OPTION

async def test_all_spin_speeds():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # Select Cotton (12)
        await client.select_program(12)
        await asyncio.sleep(1.0)
        
        speeds = [
            (0, "No Spin"),
            (1, "400 RPM"),
            (2, "600 RPM"),
            (4, "800 RPM"),
            (6, "1000 RPM"),
            (7, "1200 RPM"),
            (8, "1400 RPM"),
        ]
        
        for code, label in speeds:
            # Send [63, 07, 02, 01, 05, 0x00, code, chk1, chk2]
            pkt = [FRAME_HEADER, 0x07, CMD_TYPE_USER_OPTION, 0x01, 0x05, 0x00, code, 0x00, 0x00]
            chk1, chk2 = compute_checksums(pkt[:-2])
            pkt[-2] = chk1
            pkt[-1] = chk2
            await client._send_raw_command(bytes(pkt))
            await asyncio.sleep(0.4)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Set Spin Code {code} ({label:8s}) -> Reported: {st.spin_speed_name:8s} (code={st.spin_speed_code}, Raw[8]={hex(raw[8])})")
            assert st.spin_speed_code == code, f"Expected code {code}, got {st.spin_speed_code}"

        print("\nALL 7 SPIN SPEEDS HARDWARE VERIFIED SUCCESSFULLY!")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_all_spin_speeds())
