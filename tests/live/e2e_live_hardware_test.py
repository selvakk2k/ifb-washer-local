import asyncio
from ifb_washer_local import IFBWasherClient

async def run_e2e_tests():
    client = IFBWasherClient(host="192.168.0.100")
    try:
        print("=" * 70)
        print("STARTING LIVE END-TO-END HARDWARE VERIFICATION (192.168.0.100)")
        print("=" * 70)

        # ----------------------------------------------------------------------
        # TEST SUITE 1: COTTON PROGRAM (12)
        # ----------------------------------------------------------------------
        print("\n>>> TEST SUITE 1: Cotton (Program 12)")
        st = await client.select_program(12)
        print(f"[COTTON INITIAL] -> {st.program_name}, Spin: {st.spin_speed_name}, Temp: {st.temperature_name}")
        assert st.program_code == 12, f"Failed to select Cotton: {st.program_code}"
        await asyncio.sleep(1.0)

        # 1a. Spin Speed -> 1200 RPM (code 7)
        print("Testing set_spin_speed(7) -> 1200 RPM...")
        st = await client.set_spin_speed(spin_code=7)
        print(f"Reported Spin: {st.spin_speed_name} (code={st.spin_speed_code})")
        assert st.spin_speed_code == 7, f"Expected 1200 RPM (7), got {st.spin_speed_code}"
        await asyncio.sleep(0.8)

        # 1b. Temperature -> 60°C (code 5)
        print("Testing set_temperature(5) -> 60°C...")
        st = await client.set_temperature(temp_code=5)
        print(f"Reported Temp: {st.temperature_name} (code={st.temperature_code}), Preserved Spin: {st.spin_speed_name}")
        assert st.temperature_code == 5, f"Expected 60°C (5), got {st.temperature_code}"
        assert st.spin_speed_code == 7, f"Spin speed should be preserved at 1200 RPM, got {st.spin_speed_name}"
        await asyncio.sleep(0.8)

        # 1c. Extra Rinse -> +1 Rinse (1)
        print("Testing set_extra_rinse(1) -> +1 Rinse...")
        st = await client.set_extra_rinse(1)
        print(f"Reported Extra Rinse: {st.extra_rinse} ({st.extra_rinse_name})")
        assert st.extra_rinse == 1, f"Expected 1 extra rinse, got {st.extra_rinse}"
        await asyncio.sleep(0.8)

        # 1d. Dry Mode -> Cupboard Dry (1)
        print("Testing set_dry_mode(1) -> Cupboard Dry...")
        st = await client.set_dry_mode(1)
        print(f"Reported Dry Mode: {st.dry_mode_name} (code={st.dry_mode_code})")
        assert st.dry_mode_code == 1, f"Expected Cupboard Dry (1), got {st.dry_mode_code}"
        await asyncio.sleep(0.8)

        print("[TEST SUITE 1 PASSED]: All Cotton program controls verified on hardware.")

        # ----------------------------------------------------------------------
        # TEST SUITE 2: MIX / DAILY PROGRAM (13)
        # ----------------------------------------------------------------------
        print("\n>>> TEST SUITE 2: Mix / Daily (Program 13)")
        st = await client.select_program(13)
        print(f"[MIX/DAILY INITIAL] -> {st.program_name}, Spin: {st.spin_speed_name}, Temp: {st.temperature_name}")
        assert st.program_code == 13, f"Failed to select Mix / Daily: {st.program_code}"
        await asyncio.sleep(1.0)

        # 2a. Spin Speed -> 800 RPM (code 4)
        print("Testing set_spin_speed(4) -> 800 RPM...")
        st = await client.set_spin_speed(spin_code=4)
        print(f"Reported Spin: {st.spin_speed_name} (code={st.spin_speed_code})")
        assert st.spin_speed_code == 4, f"Expected 800 RPM (4), got {st.spin_speed_code}"
        await asyncio.sleep(0.8)

        # 2b. Temperature -> 40°C (code 4)
        print("Testing set_temperature(4) -> 40°C...")
        st = await client.set_temperature(temp_code=4)
        print(f"Reported Temp: {st.temperature_name} (code={st.temperature_code}), Preserved Spin: {st.spin_speed_name}")
        assert st.temperature_code == 4, f"Expected 40°C (4), got {st.temperature_code}"
        assert st.spin_speed_code == 4, f"Spin speed should be preserved at 800 RPM, got {st.spin_speed_name}"
        await asyncio.sleep(0.8)

        # 2c. Extra Rinse -> +2 Rinses (2)
        print("Testing set_extra_rinse(2) -> +2 Rinses...")
        st = await client.set_extra_rinse(2)
        print(f"Reported Extra Rinse: {st.extra_rinse} ({st.extra_rinse_name})")
        assert st.extra_rinse == 2, f"Expected 2 extra rinses, got {st.extra_rinse}"
        await asyncio.sleep(0.8)

        # 2d. Dry Mode -> 1 Hour (8)
        print("Testing set_dry_mode(8) -> 1 Hour...")
        st = await client.set_dry_mode(8)
        print(f"Reported Dry Mode: {st.dry_mode_name} (code={st.dry_mode_code})")
        assert st.dry_mode_code == 8, f"Expected 1 Hour (8), got {st.dry_mode_code}"
        await asyncio.sleep(0.8)

        # 2e. Clean Restore: Extra Rinse -> 0, Dry Mode -> 0
        print("Testing clean restore: set_extra_rinse(0), set_dry_mode(0)...")
        await client.set_extra_rinse(0)
        await asyncio.sleep(0.5)
        st = await client.set_dry_mode(0)
        print(f"Reported Extra Rinse: {st.extra_rinse}, Dry Mode: {st.dry_mode_name}")
        assert st.extra_rinse == 0
        assert st.dry_mode_code == 0

        print("[TEST SUITE 2 PASSED]: All Mix / Daily controls verified on hardware.")

        print("\n" + "=" * 70)
        print("SUCCESS! ALL LIVE END-TO-END HARDWARE TESTS PASSED PERFECTLY!")
        print("=" * 70)

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(run_e2e_tests())
