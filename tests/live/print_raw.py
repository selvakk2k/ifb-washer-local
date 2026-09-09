import asyncio
from ifb_washer_local import IFBWasherClient

async def print_raw():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        st = await client.get_state()
        raw = bytes.fromhex(st.raw_hex)
        print("Telemetry raw (32 bytes):")
        for i, b in enumerate(raw):
            print(f"[{i:2d}] {hex(b):4s} ({b:3d})")
        print("\nDecoded summary:")
        print(f"Program: {st.program_name} (code={st.program_code})")
        print(f"Spin: {st.spin_speed_name} (code={st.spin_speed_code})")
        print(f"Temp: {st.temperature_name} (code={st.temperature_code})")
        print(f"Extra Rinse: {st.extra_rinse}")
        print(f"Dry Mode: {st.dry_mode_name} (code={st.dry_mode_code})")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(print_raw())
