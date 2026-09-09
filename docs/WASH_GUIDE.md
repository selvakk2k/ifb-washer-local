# IFB Washing Machine & Washer Dryer Operation Guide

This guide describes how wash cycles, drying modes, cycle modifiers, and child safety features work on IFB front-load washing machines and washer-dryers.

---

## 1. Wash Programs & Recommended Use

| Program | Nominal Time | Default Temp | Default Spin | Dry Allowed? | Recommended Laundry & Best Use |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Mix / Daily** | 72 min | 40°C | 1000 RPM | Up to 3 Hours | Everyday mixed cotton and synthetic clothes (t-shirts, trousers, linens). |
| **Cotton** | 163 min | 60°C | 1400 RPM | Up to 4 Hours | Colorfast cottons, bedsheets, towels, and heavily soiled white clothes. |
| **Synthetic** | ~75 min | 40°C | 1000 RPM | Up to 3 Hours | Polyester, nylon, blended fabrics, and office attire. |
| **CradleWash®** | 37 min | 30°C | 400 RPM | Up to 1 Hour (Gentle) | Delicate garments, silks, laces, and hand-wash-only clothes. Drum rocks smoothly. |
| **Wool** | 43 min | 30°C | 800 RPM | Up to 1 Hour (Gentle) | Machine-washable woolens, sweaters, and cardigans. Prevents felt formation and shrinkage. |
| **Express 15'** | 15 min | Cold | 800 RPM | No | Lightly soiled shirts, gym clothes, or newly bought clothes that just need a quick rinse. |
| **Express 30'** | 30 min | 30°C | 1000 RPM | Up to 1 Hour | Small daily loads needing a full wash, rinse, and spin in half an hour. |
| **Anti-Allergen** | 115 min | 60°C | 1000 RPM | Up to 3 Hours | Kills house dust mites, pollen, and allergens at 60°C with intensive rinsing. |
| **Baby Wear** | ~110 min | 60°C | 800 RPM | Up to 3 Hours | Baby clothes, cloth diapers, and bibs. Ensures thorough detergent removal. |
| **Bulky / Bedding** | ~90 min | 40°C | 800 RPM | Up to 4 Hours | Comforters, blankets, bedspreads, and thick curtains requiring high water volume. |
| **Refresh** | 30 min | Cold | No Spin | No | Uses heated steam and air to de-wrinkle and remove stale odors (food, smoke) from dry clothes without water or detergent. |
| **Power Steam** | ~60 min | 40°C | 800 RPM | No | Intensive steam-assisted wash to loosen grease and stubborn dirt. |
| **Wash + Dry 2Hr** | 120 min | 40°C | 1000 RPM | Yes (Full) | Complete continuous wash and dry cycle for everyday clothes in 2 hours. |
| **Wash + Dry 4Hr** | 240 min | 40°C | 1200 RPM | Yes (Up to 6h) | Complete continuous wash and intensive dry cycle for heavy loads (towels, cottons). |
| **Steam & Dry** | ~90 min | 40°C | 1200 RPM | Yes (Up to 2h) | Steam wash followed by light drying for wrinkle-free clothes. |
| **Tub Clean** | ~90 min | 95°C | 800 RPM | No | High-temperature self-cleaning cycle to remove detergent residue and descale the drum. Run once a month. |
| **Spin Dry / Drain** | ~14 min | Cold | 1000 RPM | No | Drains standing water and spins laundry at the selected speed. Ideal for hand-washed items. |
| **Rinse + Spin** | ~20 min | Cold | 1000 RPM | No | Rinses laundry with fresh water, conditions with fabric softener, and spins. Skips main wash. |

---

## 2. Drying Modes & Timed Drying

On IFB Washer Dryers, drying can be run automatically after a wash or as a standalone cycle.

### Sensor Dry Modes (Auto Moisture Sensing)
The machine uses temperature and humidity sensors to measure clothes dryness automatically:
* **Cupboard Dry**: Dries clothes completely (0% residual moisture) so they can be folded and placed directly in your wardrobe.
* **Iron Dry**: Leaves approximately 12% residual moisture in fabrics, making it easy to iron out deep wrinkles without spraying water.
* **Eco Dry**: Energy-saving drying cycle that uses lower heater output with intermittent air cool-down phases.
* **Gentle Dry**: Lower heat drying designed for synthetic blends and delicate items.
* **Cradle Dry**: Low agitation, gentle heat drying for woolens and delicates.

### Timed Dry Options
Fixed duration drying in 30-minute steps:
* `30 Minutes`, `1 Hour`, `1 Hour 30 Minutes`, `2 Hours`, `2 Hours 30 Minutes`, `3 Hours`, `3 Hours 30 Minutes`, `4 Hours`, `4 Hours 30 Minutes`, `5 Hours`, `6 Hours`.

> [!NOTE]
> Program Gating: The machine limits maximum drying time according to the selected program. For example, Mix/Daily allows up to 3 hours, whereas heavy cotton and Wash + Dry cycles allow up to 6 hours.

---

## 3. Cycle Modifiers & Wash Options

Modifiers can be toggled before starting a cycle:

### Wash Modifiers
* **Prewash**: Adds an initial cold wash phase before the main wash. Helps lift heavy dirt, mud, and stains so dirty water is drained before the detergent wash begins.
* **Soak**: Pauses the drum periodically with detergent water to let cleaning agents penetrate stains before washing.
* **Steam**: Injects steam into the drum during the wash to relax fabric fibers, kill bacteria, and loosen tough dirt.
* **Time Saver**: Reduces cycle duration for lightly soiled clothes by optimizing rinse and tumble intervals.
* **Eco**: Adjusts water temperature and wash rhythm to save electricity while maintaining cleaning performance.

### Finishing Modifiers
* **Extra Rinse**: Adds up to 3 additional fresh-water rinse stages to ensure complete removal of detergent residue (ideal for sensitive skin).
* **Hot Rinse**: Uses warm water during the final rinse to heat the laundry, helping water drain faster during spin and cutting subsequent drying time.
* **Rinse Hold**: Holds clothes in clean rinse water after the final rinse instead of draining and spinning. Prevents wrinkles if you cannot unload the washer immediately.
* **Aroma**: Pauses the cycle before the final rinse to give you time to add fragrance conditioner, ensuring long-lasting scent.
* **Anti-Crease**: Rotates the drum gently every few minutes after the cycle ends to prevent heavy creases if clothes are left in the drum.

---

## 4. Child Lock

* **What it does**: Locks the physical machine buttons and dial to prevent accidental interruptions by children.
* **In Home Assistant**: Can be toggled on or off directly using `switch.<washer_name>_child_lock` or through the interactive lock button on the custom card.
