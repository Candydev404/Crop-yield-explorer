"""Central configuration: column definitions, labels, units, bounds and colours."""
from __future__ import annotations

from pathlib import Path

APP_TITLE = "Crop Yield Explorer"
APP_TAGLINE = "Explore agricultural data. Understand crop performance. Discover meaningful patterns."

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_PATH = ROOT_DIR / "data" / "sample_crop_yield.csv"
SAMPLE_NAME = "Sample dataset (synthetic)"
MAX_UPLOAD_MB = 10
MIN_RECOMMENDED_ROWS = 10

# Canonical column name -> metadata.
#   label : human-readable name
#   unit  : measurement unit (empty for none)
#   kind  : "category" | "numeric" | "year" | "id"
#   bounds: plausible (min, max) range used by validation; values outside are
#           treated as invalid and set to missing (with a warning).
COLUMNS: dict[str, dict] = {
    "record_id": {"label": "Record ID", "unit": "", "kind": "id"},
    "crop": {"label": "Crop type", "unit": "", "kind": "category"},
    "region": {"label": "Region", "unit": "", "kind": "category"},
    "season": {"label": "Farming season", "unit": "", "kind": "category"},
    "year": {"label": "Year", "unit": "", "kind": "year", "bounds": (1900, 2100)},
    "rainfall_mm": {"label": "Rainfall", "unit": "mm", "kind": "numeric", "bounds": (0, 10000)},
    "temperature_c": {"label": "Temperature", "unit": "°C", "kind": "numeric", "bounds": (-10, 55)},
    "fertilizer_kg_ha": {"label": "Fertilizer usage", "unit": "kg/ha", "kind": "numeric", "bounds": (0, 5000)},
    "land_area_ha": {"label": "Land area", "unit": "ha", "kind": "numeric", "bounds": (0, 1_000_000)},
    "production_tonnes": {"label": "Total production", "unit": "tonnes", "kind": "numeric", "bounds": (0, 1e9)},
    "yield_t_ha": {"label": "Crop yield", "unit": "t/ha", "kind": "numeric", "bounds": (0, 200)},
}

REQUIRED_COLUMNS = ["crop", "yield_t_ha"]
CATEGORY_COLUMNS = [c for c, m in COLUMNS.items() if m["kind"] == "category"]
NUMERIC_COLUMNS = [c for c, m in COLUMNS.items() if m["kind"] in ("numeric", "year")]
# Columns offered in correlation analysis (year is included as a time index).
CORRELATION_COLUMNS = [
    "yield_t_ha", "rainfall_mm", "temperature_c", "fertilizer_kg_ha",
    "land_area_ha", "production_tonnes", "year",
]

# Alternative spellings accepted in uploaded files (after lower-casing and
# replacing spaces/hyphens with underscores).
ALIASES = {
    "crop_type": "crop", "crop_name": "crop",
    "location": "region", "zone": "region", "area_name": "region",
    "farming_season": "season", "cropping_season": "season",
    "rainfall": "rainfall_mm", "rainfall_(mm)": "rainfall_mm", "rain_mm": "rainfall_mm",
    "temperature": "temperature_c", "temp_c": "temperature_c", "temperature_(c)": "temperature_c",
    "fertilizer": "fertilizer_kg_ha", "fertiliser": "fertilizer_kg_ha",
    "fertilizer_kg": "fertilizer_kg_ha", "fertiliser_kg_ha": "fertilizer_kg_ha",
    "land_area": "land_area_ha", "area_ha": "land_area_ha", "area": "land_area_ha",
    "production": "production_tonnes", "total_production": "production_tonnes",
    "production_t": "production_tonnes",
    "yield": "yield_t_ha", "crop_yield": "yield_t_ha", "yield_tonnes_per_ha": "yield_t_ha",
    "yield_t/ha": "yield_t_ha",
    "id": "record_id",
}

# Colour palette (colour-blind-considerate categorical colours plus
# agricultural accents for the interface).
FOREST = "#163B2D"
EVERGREEN = "#102B22"
GREEN = "#287A52"
GREEN_DARK = "#163B2D"
SAGE = "#DCE9DF"
IVORY = "#F8F7F1"
CHARCOAL = "#202923"
GREY = "#7C887F"
LIME = "#B9D977"
WHEAT = "#C99A2E"
SOIL = "#6B4F3A"
# Curated categorical palette: distinguishable hues that sit well with the green brand colours.
CATEGORICAL = [
    "#287A52", "#D9A441", "#3C7DA6", "#C4623B", "#7A5C99", "#5FB3A1",
    "#8A6F47", "#9AA64B", "#1F4E5F", "#C98BA6", "#5A6B63", "#E0C36E",
]


def label(col: str, with_unit: bool = True) -> str:
    """Return a readable axis/table label such as 'Rainfall (mm)'."""
    meta = COLUMNS.get(col)
    if meta is None:
        return col.replace("_", " ").title()
    if with_unit and meta["unit"]:
        return f"{meta['label']} ({meta['unit']})"
    return meta["label"]
