"""
parser_tradestat.py
-------------------
Parses ALL three tradestat Excel file types:

1. tradestat_commodity_export_2023_Jan.xlsx
   Columns: S. | HS Code | Commodity | CurMonVal | PrevMonVal | %Growth | CumCur | CumPrev | %Growth
   → Total India exports/imports per HS4 per month

2. tradestat_country_export_2023_Jan.xlsx
   Columns: S. | Country | CurMonVal | PrevMonVal | %Growth | CumCur | CumPrev | %Growth
   → Total India exports/imports per country per month

3. tradestat_cxc_export_2023_Apr_AUSTRALIA.xlsx
   Columns: S.No. | HSCode | Commodity | CurMonVal | PrevMonVal | %Growth | CumCur | CumPrev | %Growth
   → India exports/imports to ONE specific country, all HS4 codes per month
   → THIS IS THE KEY FILE for "what % of commodity X goes to which country"

Values: USD Million. Exports = FOB. Imports = CIF.
"""

import os, re, glob, logging
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

MONTH_MAP = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
}


# ─────────────────────────────────────────────────────────────────────────────
# Filename parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_filename(filepath: str) -> dict:
    fname  = os.path.basename(filepath).lower()
    fname  = fname.replace(".xlsx","").replace(".xls","")
    parts  = fname.split("_")

    # Determine file type
    if "cxc" in fname:
        file_type = "cxc"
    elif "commodity" in fname:
        file_type = "commodity"
    else:
        file_type = "country"

    flow = "export" if "export" in fname else "import"

    year  = next((int(p) for p in parts if p.isdigit() and len(p)==4), None)
    month = next((p for p in parts if p in MONTH_MAP), None)

    # For CXC: country is everything after the month token
    country = None
    if file_type == "cxc" and month:
        idx  = parts.index(month)
        country_parts = parts[idx+1:]
        country = "_".join(p.upper() for p in country_parts) if country_parts else None

    return {
        "file_type": file_type,
        "flow":      flow,
        "year":      year,
        "month":     month.capitalize() if month else None,
        "month_num": MONTH_MAP.get(month, 0),
        "country":   country,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Core row parser (shared by all 3 types)
# ─────────────────────────────────────────────────────────────────────────────

def _find_header_row(df: pd.DataFrame) -> int:
    """Find the row index containing column headers."""
    for i in range(min(8, len(df))):
        row_str = " ".join(str(v).lower() for v in df.iloc[i].values)
        if any(k in row_str for k in ["hscode", "hs code", "commodity", "country", "s.no"]):
            return i
    return 2


def _clean_val(v) -> float:
    """Convert cell value to float, return 0 on failure."""
    s = str(v).replace(",","").strip()
    if s in ("nan", "-", "", "na", "n/a"):
        return 0.0
    try:
        return max(0.0, float(s))
    except:
        return 0.0


def _parse_sheet(filepath: str, meta: dict) -> pd.DataFrame:
    """
    Parse any tradestat Excel sheet into a standardised DataFrame.

    Returns columns:
      date | year | month | month_num | hs_code | hs_description | country | flow | value_usd_mn
    """
    try:
        raw = pd.read_excel(filepath, header=None, dtype=str)
    except Exception as e:
        logger.error(f"Cannot read {os.path.basename(filepath)}: {e}")
        return pd.DataFrame()

    hdr = _find_header_row(raw)
    data = raw.iloc[hdr+1:].reset_index(drop=True)

    # Drop total / empty rows
    first_col = data.iloc[:,0].astype(str).str.lower()
    data = data[~first_col.str.contains(r"total|india|grand|^\s*$", na=True)]
    data = data.dropna(how="all").reset_index(drop=True)

    file_type = meta["file_type"]
    records   = []

    for _, row in data.iterrows():
        try:
            if file_type in ("commodity", "cxc"):
                # Col 1 = HS code, Col 2 = description, Col 3 = current month value
                hs = str(row.iloc[1]).strip().zfill(4)
                if not re.match(r"^\d{4}$", hs):
                    continue
                desc  = str(row.iloc[2]).strip()
                value = _clean_val(row.iloc[3])   # current month (col index 3)

            else:  # country file
                # Col 1 = country name, Col 2 = current month value
                country_name = str(row.iloc[1]).strip()
                if not country_name or country_name.lower() in ("nan","country",""):
                    continue
                if len(country_name) < 2 or country_name.isdigit():
                    continue
                hs    = ""
                desc  = ""
                value = _clean_val(row.iloc[2])

            records.append({
                "date":            f"{meta['year']}-{meta['month_num']:02d}-01",
                "year":            meta["year"],
                "month":           meta["month"],
                "month_num":       meta["month_num"],
                "hs_code":         hs,
                "hs_description":  desc,
                "country":         meta["country"] if file_type == "cxc" else (
                                       country_name if file_type == "country" else "ALL"),
                "flow":            meta["flow"],
                "value_usd_mn":    round(value, 4),
            })

        except (IndexError, ValueError):
            continue

    df = pd.DataFrame(records)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Master loader
# ─────────────────────────────────────────────────────────────────────────────

def load_all_files(folder: str, show_progress: bool = True) -> dict:
    """
    Load ALL tradestat Excel files from folder.

    Returns:
      {
        "commodity": DataFrame,   # HS4 totals (all countries combined)
        "country":   DataFrame,   # country totals (all commodities combined)
        "cxc":       DataFrame,   # HS4 × country (the key cross-tab data)
      }
    """
    files = (glob.glob(os.path.join(folder, "*.xlsx")) +
             glob.glob(os.path.join(folder, "*.xls")))

    if not files:
        logger.warning(f"No Excel files in: {folder}")
        return {"commodity": pd.DataFrame(), "country": pd.DataFrame(), "cxc": pd.DataFrame()}

    logger.info(f"Found {len(files)} files in {folder}")

    buckets  = {"commodity": [], "country": [], "cxc": []}
    skipped  = 0
    total    = len(files)

    for i, fpath in enumerate(sorted(files), 1):
        meta = parse_filename(fpath)
        if not meta["year"] or not meta["month"]:
            skipped += 1
            continue

        if show_progress and i % 50 == 0:
            logger.info(f"  Progress: {i}/{total} files ...")

        df = _parse_sheet(fpath, meta)
        if not df.empty:
            buckets[meta["file_type"]].append(df)

    result = {}
    for key, frames in buckets.items():
        if frames:
            combined = pd.concat(frames, ignore_index=True)
            combined["date"] = pd.to_datetime(combined["date"])
            combined = combined.sort_values(["date","hs_code"] if key != "country" else ["date","country"])
            result[key] = combined
            logger.info(f"  {key:10s}: {len(combined):>8,} rows | "
                        f"{combined['date'].min().strftime('%b %Y')} - "
                        f"{combined['date'].max().strftime('%b %Y')}")
        else:
            result[key] = pd.DataFrame()

    if skipped:
        logger.warning(f"  Skipped {skipped} files (bad filename format)")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Build analysis tables
# ─────────────────────────────────────────────────────────────────────────────

def build_commodity_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """commodity file → wide: export + import columns."""
    if df is None or df.empty:
        return pd.DataFrame()
    key = ["date","year","month","month_num","hs_code","hs_description"]
    exp = df[df["flow"]=="export"][key+["value_usd_mn"]].rename(columns={"value_usd_mn":"export_usd_mn"})
    imp = df[df["flow"]=="import"][key+["value_usd_mn"]].rename(columns={"value_usd_mn":"import_usd_mn"})
    merged = pd.merge(exp, imp, on=key, how="outer").fillna(0)
    merged["trade_balance"] = merged["export_usd_mn"] - merged["import_usd_mn"]
    return merged.sort_values(["date","hs_code"])


def build_country_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """country file → wide: export + import columns."""
    if df is None or df.empty:
        return pd.DataFrame()
    key = ["date","year","month","month_num","country"]
    exp = df[df["flow"]=="export"][key+["value_usd_mn"]].rename(columns={"value_usd_mn":"export_usd_mn"})
    imp = df[df["flow"]=="import"][key+["value_usd_mn"]].rename(columns={"value_usd_mn":"import_usd_mn"})
    merged = pd.merge(exp, imp, on=key, how="outer").fillna(0)
    merged["trade_balance"] = merged["export_usd_mn"] - merged["import_usd_mn"]
    return merged.sort_values(["date","country"])


def build_cxc_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """
    CXC file → wide: HS4 × country × month
    export_usd_mn + import_usd_mn + % share columns.
    This is the CORE table for commodity-country analysis.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    key = ["date","year","month","month_num","hs_code","hs_description","country"]
    exp = df[df["flow"]=="export"][key+["value_usd_mn"]].rename(columns={"value_usd_mn":"export_usd_mn"})
    imp = df[df["flow"]=="import"][key+["value_usd_mn"]].rename(columns={"value_usd_mn":"import_usd_mn"})
    merged = pd.merge(exp, imp, on=key, how="outer").fillna(0)
    merged["trade_balance"] = merged["export_usd_mn"] - merged["import_usd_mn"]

    # Add % share per HS code per month
    tot_exp = merged.groupby(["date","hs_code"])["export_usd_mn"].transform("sum")
    tot_imp = merged.groupby(["date","hs_code"])["import_usd_mn"].transform("sum")
    merged["export_share_pct"] = (merged["export_usd_mn"] / tot_exp.replace(0,np.nan) * 100).round(2).fillna(0)
    merged["import_share_pct"] = (merged["import_usd_mn"] / tot_imp.replace(0,np.nan) * 100).round(2).fillna(0)

    return merged.sort_values(["date","hs_code","export_usd_mn"], ascending=[True,True,False])


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(data: dict):
    print("\n" + "="*65)
    print("  TRADESTAT DATA LOADED")
    print("="*65)
    for key, df in data.items():
        if df is not None and not df.empty:
            print(f"\n  [{key.upper()}]")
            print(f"  Rows       : {len(df):,}")
            if "hs_code" in df.columns:
                print(f"  HS codes   : {df['hs_code'].nunique():,}")
            if "country" in df.columns and key != "commodity":
                print(f"  Countries  : {df['country'].nunique():,}")
            print(f"  Date range : {df['date'].min().strftime('%b %Y')} - "
                  f"{df['date'].max().strftime('%b %Y')}")
            print(f"  Flows      : {sorted(df['flow'].unique().tolist())}")

            # Top 5 by latest month
            latest = df["date"].max()
            exp = df[(df["date"]==latest) & (df["flow"]=="export")]
            if not exp.empty:
                sort_col = "hs_code" if key=="commodity" else "country" if key=="country" else "hs_code"
                top = exp.nlargest(5, "value_usd_mn")
                label = "HS" if key in ("commodity","cxc") else "Country"
                print(f"\n  TOP 5 EXPORTS ({latest.strftime('%b %Y')}):")
                for _, r in top.iterrows():
                    name = r.get("hs_code","?") if key in ("commodity","cxc") else r.get("country","?")
                    desc = r.get("hs_description","")[:35]
                    ctry = f" → {r.get('country','')}" if key == "cxc" else ""
                    print(f"    {label} {name}{ctry} | {desc} | USD {r['value_usd_mn']:,.1f} Mn")
    print("="*65 + "\n")


if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s")
    folder = sys.argv[1] if len(sys.argv) > 1 else "data/raw/tradestat"
    data   = load_all_files(folder)
    print_summary(data)
