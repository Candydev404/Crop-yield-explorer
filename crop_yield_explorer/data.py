"""Loading, validating and cleaning crop yield datasets.

Every function here is free of Streamlit calls so it can be unit-tested.
Invalid input never raises to the caller: problems are reported through the
``errors`` and ``warnings`` lists of :class:`LoadResult`.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config

ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


@dataclass
class LoadResult:
    """Outcome of loading a dataset."""

    df: pd.DataFrame | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    rows_read: int = 0
    rows_kept: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors and self.df is not None and len(self.df) > 0


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------
def read_csv_bytes(raw: bytes) -> tuple[pd.DataFrame | None, str | None]:
    """Parse CSV bytes. Returns (dataframe, error_message)."""
    if raw is None or len(raw.strip()) == 0:
        return None, "The file is empty."
    if len(raw) > config.MAX_UPLOAD_MB * 1024 * 1024:
        return None, f"The file is larger than the {config.MAX_UPLOAD_MB} MB limit."
    if b"\x00" in raw[:4096]:
        return None, "The file looks like a binary file, not a text CSV file."
    last_err = None
    for enc in ENCODINGS:
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError as exc:  # try next encoding
            last_err = exc
            continue
        try:
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python", skipinitialspace=True)
        except pd.errors.EmptyDataError:
            return None, "The file contains no data."
        except (pd.errors.ParserError, csv.Error) as exc:
            return None, f"The file could not be parsed as CSV ({exc})."
        except Exception as exc:  # defensive: never crash the app
            return None, f"The file could not be read as CSV ({type(exc).__name__}: {exc})."
        return df, None
    return None, f"The file encoding is not supported ({last_err})."


def _normalise_name(name: object) -> str:
    s = str(name).strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)
    return config.ALIASES.get(s, s)


# --------------------------------------------------------------------------
# Validation and cleaning
# --------------------------------------------------------------------------
def validate_and_clean(raw_df: pd.DataFrame | None) -> LoadResult:
    """Validate a raw dataframe against the expected schema and clean it."""
    res = LoadResult()
    if raw_df is None or raw_df.empty:
        res.errors.append("The file has no data rows.")
        return res
    res.rows_read = len(raw_df)
    df = raw_df.copy()

    # Column names ---------------------------------------------------------
    df.columns = [_normalise_name(c) for c in df.columns]
    if df.columns.duplicated().any():
        dups = sorted(set(df.columns[df.columns.duplicated()]))
        res.warnings.append(
            "Duplicate column names after standardisation were found (" + ", ".join(dups)
            + "). Only the first occurrence of each was kept."
        )
        df = df.loc[:, ~df.columns.duplicated()]
    known = [c for c in df.columns if c in config.COLUMNS]
    ignored = [c for c in df.columns if c not in config.COLUMNS]
    if ignored:
        res.notes.append("Columns not used by the application were ignored: " + ", ".join(map(str, ignored)) + ".")
    df = df[known]

    # Derive yield when it can be computed ------------------------------------
    if "yield_t_ha" not in df.columns and {"production_tonnes", "land_area_ha"} <= set(df.columns):
        prod = pd.to_numeric(df["production_tonnes"], errors="coerce")
        area = pd.to_numeric(df["land_area_ha"], errors="coerce")
        df["yield_t_ha"] = (prod / area.where(area > 0)).round(2)
        res.notes.append("The 'yield_t_ha' column was derived as production_tonnes / land_area_ha.")

    missing_req = [c for c in config.REQUIRED_COLUMNS if c not in df.columns]
    if missing_req:
        res.errors.append(
            "Required column(s) missing: " + ", ".join(missing_req)
            + ". The file must contain a crop column and a yield column (or production and land area "
              "so that yield can be calculated). Recognised column names: "
            + ", ".join(config.COLUMNS) + "."
        )
        return res

    # Text columns ----------------------------------------------------------------
    for col in config.CATEGORY_COLUMNS:
        if col in df.columns:
            s = df[col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
            s = s.replace("", pd.NA).str.title()
            df[col] = s.astype(object).where(s.notna(), np.nan)

    # Numeric columns --------------------------------------------------------------
    for col in config.NUMERIC_COLUMNS:
        if col not in df.columns:
            continue
        before = df[col].notna() & (df[col].astype("string").str.strip() != "")
        num = pd.to_numeric(df[col], errors="coerce")
        bad = int((before & num.isna()).sum())
        if bad:
            examples = df.loc[before & num.isna(), col].astype(str).unique()[:3]
            res.warnings.append(
                f"{bad} value(s) in '{col}' are not numeric (e.g. {', '.join(examples)}) "
                "and were treated as missing."
            )
        lo, hi = config.COLUMNS[col]["bounds"]
        out = num.notna() & ((num < lo) | (num > hi))
        if col == "land_area_ha":
            out = num.notna() & ((num <= lo) | (num > hi))
        if out.any():
            res.warnings.append(
                f"{int(out.sum())} value(s) in '{col}' are outside the plausible range "
                f"({lo:g} to {hi:g}) and were treated as missing."
            )
            num = num.mask(out)
        df[col] = num
    if "year" in df.columns:
        yr = df["year"]
        non_int = yr.notna() & (yr != yr.round())
        if non_int.any():
            res.warnings.append(f"{int(non_int.sum())} non-integer year value(s) were treated as missing.")
            yr = yr.mask(non_int)
        df["year"] = yr.round().astype("Int64")

    # Drop unusable rows ------------------------------------------------------------
    unusable = df["crop"].isna() | df["yield_t_ha"].isna()
    if unusable.any():
        res.warnings.append(
            f"{int(unusable.sum())} row(s) had no crop name or no usable yield value and were excluded."
        )
        df = df[~unusable]
    n_dup = int(df.duplicated().sum())
    if n_dup:
        res.warnings.append(f"{n_dup} exact duplicate row(s) were removed.")
        df = df.drop_duplicates()

    if df.empty:
        res.errors.append("No usable records remain after validation. Check the crop and yield columns.")
        return res

    # Consistency checks (reported, not altered) ---------------------------------------
    if {"production_tonnes", "land_area_ha", "yield_t_ha"} <= set(df.columns):
        calc = df["production_tonnes"] / df["land_area_ha"]
        rel = (calc - df["yield_t_ha"]).abs() / df["yield_t_ha"].where(df["yield_t_ha"] > 0)
        n_incons = int((rel > 0.05).sum())
        if n_incons:
            res.warnings.append(
                f"{n_incons} record(s) have a yield that differs by more than 5% from "
                "production divided by land area. Values were kept as supplied."
            )
    if len(df) < config.MIN_RECOMMENDED_ROWS:
        res.warnings.append(
            f"Only {len(df)} usable record(s) were found. Statistics and correlations are unreliable "
            f"with fewer than {config.MIN_RECOMMENDED_ROWS} records."
        )
    if df["crop"].nunique() > 12:
        res.warnings.append(
            f"The file contains {df['crop'].nunique()} different crop names; charts may be crowded."
        )

    df = df.reset_index(drop=True)
    res.df = df
    res.rows_kept = len(df)
    return res


def load_csv_bytes(raw: bytes) -> LoadResult:
    """Read, validate and clean uploaded CSV bytes."""
    raw_df, err = read_csv_bytes(raw)
    if err:
        return LoadResult(errors=[err])
    try:
        return validate_and_clean(raw_df)
    except Exception as exc:  # defensive: unexpected data shapes must not crash the UI
        return LoadResult(errors=[f"The file could not be validated ({type(exc).__name__}: {exc})."])


def load_sample() -> LoadResult:
    """Load the bundled synthetic sample dataset."""
    try:
        raw = config.SAMPLE_PATH.read_bytes()
    except OSError as exc:
        return LoadResult(errors=[f"The sample dataset could not be found ({exc})."])
    return load_csv_bytes(raw)


# --------------------------------------------------------------------------
# Descriptions used by the Data page
# --------------------------------------------------------------------------
def schema_table(df: pd.DataFrame) -> pd.DataFrame:
    """Column names, data types, completeness and an example value."""
    rows = []
    for col in df.columns:
        s = df[col]
        nonnull = s.dropna()
        rows.append({
            "Column": col,
            "Description": config.label(col),
            "Data type": str(s.dtype),
            "Non-missing": int(s.notna().sum()),
            "Missing": int(s.isna().sum()),
            "Unique values": int(s.nunique(dropna=True)),
            "Example": str(nonnull.iloc[0]) if len(nonnull) else "",
        })
    return pd.DataFrame(rows)


def missing_table(df: pd.DataFrame) -> pd.DataFrame:
    """Missing-value counts and percentages per column, largest first."""
    miss = df.isna().sum()
    out = pd.DataFrame({
        "Column": miss.index,
        "Missing values": miss.values,
        "Missing (%)": (miss.values / max(len(df), 1) * 100).round(2),
    })
    return out.sort_values(["Missing values", "Column"], ascending=[False, True]).reset_index(drop=True)
