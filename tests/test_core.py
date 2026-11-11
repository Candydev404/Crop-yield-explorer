"""Unit tests for loading, validation, filtering and statistics."""
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from crop_yield_explorer import data, filters, stats  # noqa: E402


def _csv(text: str) -> bytes:
    return text.encode("utf-8")


GOOD = "crop,region,year,rainfall_mm,yield_t_ha,production_tonnes,land_area_ha\n" + "\n".join(
    f"Maize,North,{2015 + i % 5},{600 + i * 10},{2 + i * 0.1:.1f},{(2 + i * 0.1) * 2:.2f},2" for i in range(15)
)


def test_sample_loads_and_is_valid():
    res = data.load_sample()
    assert res.ok
    assert len(res.df) == 720
    assert res.df["crop"].nunique() == 8
    assert res.df["yield_t_ha"].min() > 0


def test_good_csv_loads():
    res = data.load_csv_bytes(_csv(GOOD))
    assert res.ok and res.rows_kept == 15


@pytest.mark.parametrize("raw,fragment", [
    (b"", "empty"),
    (b"   \n  ", "empty"),
    (b"\x00\x01\x02binary", "binary"),
    (_csv("a,b\n1,2\n3,4\n"), "Required column"),
    (_csv("crop,yield_t_ha\n"), "no data"),
])
def test_invalid_files_report_errors_without_raising(raw, fragment):
    res = data.load_csv_bytes(raw)
    assert not res.ok
    assert any(fragment.lower() in e.lower() for e in res.errors)


def test_aliases_and_derived_yield():
    raw = _csv("Crop Type,Location,Production,Land Area\n" + "\n".join(f"Rice,A,{10 + i},{2}" for i in range(12)))
    res = data.load_csv_bytes(raw)
    assert res.ok
    assert {"crop", "region", "yield_t_ha"} <= set(res.df.columns)
    assert res.df["yield_t_ha"].iloc[0] == pytest.approx(5.0)


def test_non_numeric_and_out_of_range_become_missing():
    rows = ["crop,yield_t_ha,rainfall_mm,temperature_c"]
    rows += [f"Maize,{2 + i * 0.1},{500 + i},{25}" for i in range(12)]
    rows += ["Maize,3.0,abc,25", "Maize,3.0,500,999"]
    res = data.load_csv_bytes(_csv("\n".join(rows)))
    assert res.ok
    assert res.df["rainfall_mm"].isna().sum() == 1
    assert res.df["temperature_c"].isna().sum() == 1
    assert len(res.warnings) >= 2


def test_rows_without_yield_dropped_and_duplicates_removed():
    rows = ["crop,yield_t_ha"] + [f"Maize,{i}" for i in range(1, 13)] + ["Maize,", ",5", "Maize,1"]
    res = data.load_csv_bytes(_csv("\n".join(rows)))
    assert res.ok and res.rows_kept == 12
    assert any("excluded" in w for w in res.warnings)
    assert any("duplicate" in w for w in res.warnings)


def test_semicolon_delimiter_and_latin1_encoding():
    text = "crop;yield_t_ha\n" + "\n".join(f"Maïze;{1 + i / 10}" for i in range(12))
    res = data.load_csv_bytes(text.encode("latin-1"))
    assert res.ok and res.rows_kept == 12


def test_filters_numeric_and_category():
    df = data.load_sample().df
    full = {"year": (2015, 2024)}
    crit = filters.Criteria({"crop": ["Maize"]}, {"year": (2020, 2024)})
    out = filters.apply_filters(df, crit, full)
    assert set(out["crop"]) == {"Maize"} and out["year"].min() >= 2020


def test_full_range_keeps_missing_values_but_narrow_range_excludes_them():
    df = data.load_sample().df
    lo, hi, _ = filters.range_bounds(df["rainfall_mm"])
    full = {"rainfall_mm": (lo, hi)}
    kept = filters.apply_filters(df, filters.Criteria({}, {"rainfall_mm": (lo, hi)}), full)
    assert len(kept) == len(df)
    narrow = filters.apply_filters(df, filters.Criteria({}, {"rainfall_mm": (lo + 1, hi)}), full)
    assert narrow["rainfall_mm"].notna().all()


def test_filter_to_nothing_returns_empty_frame():
    df = data.load_sample().df
    assert filters.apply_filters(df, filters.Criteria({"crop": []}, {}), {}).empty


def test_kpis_and_describe_match_pandas():
    df = data.load_sample().df
    k = stats.kpis(df)
    assert k["records"] == 720
    assert k["mean_yield"] == pytest.approx(df["yield_t_ha"].mean())
    assert k["total_production"] == pytest.approx(df["production_tonnes"].sum())
    d = stats.describe_numeric(df, ["yield_t_ha"]).iloc[0]
    assert d["Std. deviation"] == pytest.approx(df["yield_t_ha"].std(ddof=1))
    assert d["Median"] == pytest.approx(df["yield_t_ha"].median())


def test_correlation_matches_numpy_and_handles_degenerate_input():
    df = data.load_sample().df
    r, n = stats.pair_correlation(df, "rainfall_mm")
    pair = df[["rainfall_mm", "yield_t_ha"]].dropna()
    assert n == len(pair)
    assert r == pytest.approx(np.corrcoef(pair["rainfall_mm"], pair["yield_t_ha"])[0, 1])
    tiny = df.head(2)
    assert np.isnan(stats.pair_correlation(tiny, "rainfall_mm")[0])
    assert stats.correlation_matrix(tiny.assign(rainfall_mm=1.0, temperature_c=1.0), ["rainfall_mm", "temperature_c"]).empty


def test_strength_labels():
    assert stats.strength_label(0.05) == "negligible"
    assert stats.strength_label(-0.35) == "moderate"
    assert stats.strength_label(0.9) == "very strong"
