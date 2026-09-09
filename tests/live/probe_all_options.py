import asyncio
from ifb_washer_local import IFBWasherClient
from ifb_washer_local.protocol import build_user_option_command

async def probe_all():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        # Reset to Mix / Daily
        await client.select_program(13)
        await asyncio.sleep(1.0)
        st = await client.get_state()
        print(f"Fresh Mix / Daily state: Spin={st.spin_speed_name} (Raw[8]={hex(bytes.fromhex(st.raw_hex)[8])}), Temp={st.temperature_name}")

        # Let's test sending Option IDs 1..32 with value 7 (1200 RPM code)
        for opt_id in range(1, 33):
            # Only test non-destructive IDs or observe changes
            pkt = build_user_option_command(opt_id, 7)
            await client._send_raw_command(pkt)
            await asyncio.sleep(0.3)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex)
            if raw[8] != 0x06 or raw[10] != 0x02 or raw[9] != 0:
                print(f"*** OPTION ID {opt_id:2d} (val=7) CHANGED STATE -> Spin: {st.spin_speed_name} (Raw[8]={hex(raw[8])}), Temp: {st.temperature_name} (Raw[10]={hex(raw[10])}), Raw[9]={hex(raw[9])}, Raw[28]={hex(raw[28])}")
            # Reset back to 13 if program jumped
            if st.program_code != 13:
                await client.select_program(13)
                await asyncio.sleep(0.5)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(probe_all())
