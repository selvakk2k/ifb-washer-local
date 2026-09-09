import asyncio
import time
from ifb_washer_local import IFBWasherClient

async def monitor():
    client = IFBWasherClient(host="192.168.0.100")
    print("=" * 70)
    print("LIVE HARDWARE MONITOR ACTIVE (192.168.0.100)")
    print("Interact with the physical machine panel (dial, spin, temp, etc.)")
    print("=" * 70)
    
    last_raw = ""
    try:
        while True:
            try:
                st = await client.get_state()
                raw = bytes.fromhex(st.raw_hex)
                raw_hex = st.raw_hex
                
                if raw_hex != last_raw:
                    last_raw = raw_hex
                    ts = time.strftime("%H:%M:%S")
                    print(f"[{ts}] Prog: {st.program_name:15s} (code={st.program_code:2d}) | Spin: {st.spin_speed_name:10s} (code={st.spin_speed_code:2d}, raw[8]={hex(raw[8])}) | Temp: {st.temperature_name:6s} | RinseHold: {st.rinse_hold!s:5s} | Raw[5..12]: {[hex(b) for b in raw[5:13]]}")
            except Exception as e:
                print(f"Poll error: {e}")
            await asyncio.sleep(0.4)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(monitor())
