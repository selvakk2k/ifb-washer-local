import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import build_user_option_command, HIL_OPTION_SPIN

async def test_mix_daily_spins():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        print("=== PROBING MIX / DAILY SPIN SPEEDS ON HARDWARE ===")
        # Select Mix / Daily (13)
        await client.select_program(13)
        await asyncio.sleep(1.0)
        st = await client.get_state()
        print(f"Mix / Daily default: Spin={st.spin_speed_name} (code={st.spin_speed_code}), Rinse Hold={st.rinse_hold}")
        print(f"Raw[7..12]: {[hex(b) for b in bytes.fromhex(st.raw_hex)[7:13]]}")

        # Test each spin code on Mix / Daily:
        for code, label in [(0, "No Spin"), (1, "400 RPM"), (2, "600 RPM"), (4, "800 RPM"), (6, "1000 RPM"), (7, "1200 RPM"), (8, "1400 RPM")]:
            print(f"\nSending Spin Code {code} ({label})...")
            pkt = build_user_option_command(HIL_OPTION_SPIN, code)
            await client._send_raw_command(pkt)
            await asyncio.sleep(0.5)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            print(f"Result -> Reported Spin: {st.spin_speed_name} (code={st.spin_speed_code}, Raw[8]={hex(raw[8])}), Rinse Hold: {st.rinse_hold} (Raw[11]={hex(raw[11])})")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_mix_daily_spins())
