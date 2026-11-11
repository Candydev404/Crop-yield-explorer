"""Generate the SYNTHETIC sample dataset used by the Crop Yield Data Explorer.

The records are produced by a seeded random process with simple, documented
assumptions (crop base yields, a saturating response to fertiliser, a
penalty for water stress and for temperatures far from a crop optimum, a small
upward time trend and random noise).  They are NOT observations from real
farms and must not be cited as agricultural research findings.

Run from the project root:   python scripts/generate_sample_data.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 65
N_RECORDS = 720
OUT = Path(__file__).resolve().parent.parent / "data" / "sample_crop_yield.csv"

# crop: (base yield t/ha, water requirement mm, optimum temp C, fertiliser gain)
CROPS = {
    "Maize": (2.3, 600, 26.0, 0.55),
    "Rice": (2.9, 900, 27.0, 0.45),
    "Sorghum": (1.5, 450, 28.0, 0.30),
    "Millet": (1.1, 400, 28.0, 0.25),
    "Groundnut": (1.4, 500, 27.0, 0.15),
    "Soybean": (1.6, 550, 26.0, 0.12),
    "Cassava": (10.5, 1000, 27.0, 0.25),
    "Yam": (9.0, 1100, 26.0, 0.30),
}
REGIONS = ["North West", "North East", "North Central", "South West", "South East", "South South"]
# mean season rainfall (mm) rainy / dry, mean temperature rainy
RAIN = {"North West": (780, 15), "North East": (640, 10), "North Central": (1100, 40),
        "South West": (1250, 90), "South East": (1750, 120), "South South": (2100, 180)}
TEMP = {"North West": 27.5, "North East": 28.0, "North Central": 26.5,
        "South West": 26.5, "South East": 26.0, "South South": 26.0}
# crop weights by region (rows follow CROPS order)
W = {
    "North West":    [3, 2, 4, 4, 2, 1, 1, 1],
    "North East":    [3, 2, 4, 4, 2, 1, 1, 1],
    "North Central": [3, 3, 2, 1, 2, 3, 2, 4],
    "South West":    [3, 1, 0.5, 0.2, 1, 1, 4, 3],
    "South East":    [2, 1, 0.2, 0.1, 1, 1, 4, 4],
    "South South":   [2, 2, 0.1, 0.1, 0.5, 1, 4, 3],
}


def build() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    crops = list(CROPS)
    rows = []
    for i in range(N_RECORDS):
        region = rng.choice(REGIONS)
        w = np.array(W[region], dtype=float)
        crop = rng.choice(crops, p=w / w.sum())
        base, need, t_opt, gain = CROPS[crop]
        season = "Dry" if rng.random() < 0.18 and crop in ("Maize", "Rice", "Sorghum", "Groundnut", "Soybean") else "Rainy"
        year = int(rng.integers(2015, 2025))

        r_mean = RAIN[region][0 if season == "Rainy" else 1]
        rain = max(5.0, rng.normal(r_mean, 0.16 * r_mean))
        temp = TEMP[region] + (1.5 if season == "Dry" else 0.0) + rng.normal(0, 1.1)
        fert = 0.0 if rng.random() < 0.12 else float(np.clip(rng.gamma(2.2, 30), 5, 220))
        area = float(np.clip(rng.lognormal(np.log(3.0), 0.8), 0.4, 30))

        irrigation = rng.uniform(200, 450) if season == "Dry" else 0.0
        ratio = (rain + irrigation) / need
        f_water = 1 - 0.6 * max(0, 1 - ratio) ** 1.5 - 0.15 * max(0, ratio - 1.5)
        f_temp = max(0.6, 1 - 0.012 * (temp - t_opt) ** 2)
        f_fert = 1 + gain * (1 - np.exp(-fert / 60))
        f_year = 1.01 ** (year - 2015)
        noise = rng.lognormal(0, 0.12)
        yld = base * f_water * f_temp * f_fert * f_year * noise

        area = round(area, 1)
        production = round(yld * area, 2)
        rows.append({
            "record_id": f"R{i + 1:04d}",
            "crop": crop, "region": region, "season": season, "year": year,
            "rainfall_mm": round(rain, 1), "temperature_c": round(temp, 1),
            "fertilizer_kg_ha": round(fert, 1), "land_area_ha": area,
            "production_tonnes": production,
            "yield_t_ha": round(production / area, 2),
        })
    df = pd.DataFrame(rows)

    # Introduce a few missing values so the missing-value tools can be demonstrated.
    for col, n in (("fertilizer_kg_ha", 12), ("rainfall_mm", 8), ("temperature_c", 6)):
        idx = rng.choice(df.index, size=n, replace=False)
        df.loc[idx, col] = np.nan
    return df


if __name__ == "__main__":
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUT, index=False)
    print(f"Wrote {len(data)} synthetic records to {OUT}")
    print(data.groupby("crop")["yield_t_ha"].agg(["count", "mean"]).round(2))
