import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import compute_checksums, FRAME_HEADER, CMD_TYPE_PROGRAM_SELECT

async def test_exact_alignment():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # We test:
        # Program = 12 (Cotton), Spin = 8 (1400 RPM), Temp = 5 (60°C)
        # Program = 13 (Mix/Daily), Spin = 7 (1200 RPM), Temp = 4 (40°C)
        
        for prog, spin, temp, label in [
            (12, 8, 5, "Cotton: Spin 1400, Temp 60°C"),
            (12, 7, 4, "Cotton: Spin 1200, Temp 40°C"),
            (13, 7, 4, "Mix/Daily: Spin 1200, Temp 40°C"),
            (13, 6, 3, "Mix/Daily: Spin 1000, Temp 30°C"),
        ]:
            # Exact telemetry alignment:
            # byte 6 = prog, byte 8 = spin, byte 10 = temp
            pkt = [
                FRAME_HEADER, # 0
                0x13,         # 1
                CMD_TYPE_PROGRAM_SELECT, # 2
                0x00,         # 3
                0x00,         # 4
                0x00,         # 5
                prog,         # 6
                0x00,         # 7
                spin,         # 8
                0x00,         # 9
                temp,         # 10
                0x00,         # 11
                0x00,         # 12
                0x00,         # 13
                0x00,         # 14
                0x00,         # 15
                0x00,         # 16
                0x00,         # 17
                0x00,         # 18
                0x00,         # 19
                0x00,         # 20
            ]
            chk1, chk2 = compute_checksums(pkt[:-2])
            pkt[-2] = chk1
            pkt[-1] = chk2
            
            print(f"\n--- Testing {label} ---")
            print(f"Packet: {bytes(pkt).hex()}")
            await client._send_raw_command(bytes(pkt))
            await asyncio.sleep(1.0)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Result -> Prog: {st.program_name} (code={st.program_code}), Spin: {st.spin_speed_name} (code={st.spin_speed_code}), Temp: {st.temperature_name} (code={st.temperature_code})")
            print(f"Raw[5..12]: {[hex(b) for b in raw[5:13]]}")
            
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_exact_alignment())
