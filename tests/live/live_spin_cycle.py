import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import build_user_option_command, HIL_OPTION_SPIN

async def test_spin_cycle():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # Reset Cotton (12) -> default 1400 RPM
        print("Selecting Cotton (12)...")
        await client.select_program(12)
        await asyncio.sleep(1.0)
        st = await client.get_state()
        print(f"Cotton initial -> Spin: {st.spin_speed_name} (code={st.spin_speed_code})")

        for i in range(10):
            # Send button pulse
            pkt = build_user_option_command(HIL_OPTION_SPIN, 1)
            await client._send_raw_command(pkt)
            await asyncio.sleep(0.5)
            st = await client.get_state()
            print(f"Pulse {i+1} -> Spin: {st.spin_speed_name} (code={st.spin_speed_code}), Rinse Hold: {st.rinse_hold}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_spin_cycle())
