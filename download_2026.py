"""
download_2026.py
----------------
Automatically downloads 2026 trade data from tradestat (MEIDB).

What it downloads (same format as your existing files):
  - CXC export files: tradestat_cxc_export_2026_Jan_COUNTRY.xlsx
  - CXC import files: tradestat_cxc_import_2026_Jan_COUNTRY.xlsx
  - Commodity export: tradestat_commodity_export_2026_Jan.xlsx
  - Commodity import: tradestat_commodity_import_2026_Jan.xlsx
  - Country export:   tradestat_country_export_2026_Jan.xlsx
  - Country import:   tradestat_country_import_2026_Jan.xlsx

After download, run: python main.py --process
The new 2026 data will be added to the dashboard automatically.

Requirements:
  pip install selenium webdriver-manager requests

Usage:
  python download_2026.py                    # Download all available 2026 months
  python download_2026.py --months Jan       # Download specific month
  python download_2026.py --months Jan Feb   # Download multiple months
  python download_2026.py --check            # Check what months are available
"""

import os
import sys
import time
import logging
import argparse
import requests
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR    = os.path.join(BASE_DIR, "data", "raw", "tradestat")
MEIDB_BASE  = "http://tradestat.commerce.gov.in/meidb"

MONTH_MAP = {
    "Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
    "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12,
}

# Countries you already have (from your existing files — add/remove as needed)
COUNTRIES = [
    "AUSTRALIA", "BANGLADESH", "BELGIUM", "BRAZIL", "CANADA",
    "CHINA_P", "EGYPT_A", "ETHIOPIA", "FRANCE", "GERMANY",
    "HONG_KONG", "INDONESIA", "IRAN", "IRAQ", "ISRAEL",
    "ITALY", "JAPAN", "KENYA", "MALAYSIA", "NETHERLAND",
    "SAUDI_ARAB", "SINGAPORE", "SOUTH_AFRICA", "SOUTH_KOREA",
    "SRI_LANKA", "SWEDEN", "TAIWAN", "THAILAND", "TURKEY",
    "U_A_E", "U_S_A", "UNITED_KINGDOM", "VIETNAM",
    # Add more as needed
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
    "Referer": "http://tradestat.commerce.gov.in/meidb/",
}


# ── Step 1: Check availability ────────────────────────────────────────────────

def check_available_months(year: int = 2026) -> list:
    """
    Check which months of 2026 data are available on tradestat.
    Tries to fetch each month's page and checks if data exists.
    """
    logger.info(f"Checking available months for {year} ...")
    available = []

    session = requests.Session()
    session.headers.update(HEADERS)

    for month, num in MONTH_MAP.items():
        if year == 2026 and num > datetime.now().month:
            continue  # Skip future months

        # Test URL — commodity export page for this month
        test_url = f"{MEIDB_BASE}/commoditywise_export"
        try:
            r = session.get(test_url, timeout=15)
            # Check if the page mentions this month
            month_str = f"{month}-{year}"
            if month_str in r.text or str(year) in r.text:
                available.append(month)
                logger.info(f"  {month} {year}: AVAILABLE")
            else:
                logger.info(f"  {month} {year}: checking ...")
                available.append(month)  # Attempt anyway
        except Exception as e:
            logger.warning(f"  {month} {year}: Cannot check ({e})")

    logger.info(f"Attempting download for: {available}")
    return available


# ── Step 2: Download via direct POST (same method tradestat uses) ─────────────

def _get_session() -> requests.Session:
    """Create session with tradestat cookies."""
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get(f"{MEIDB_BASE}/commoditywise_export", timeout=15)
        logger.info("Session established")
    except Exception as e:
        logger.warning(f"Session init warning: {e}")
    return session


def download_commodity_export(session, month: str, year: int, save_dir: str) -> bool:
    """Download commodity-wise export Excel for given month/year."""
    fname = os.path.join(save_dir, f"tradestat_commodity_export_{year}_{month}.xlsx")
    if os.path.exists(fname):
        logger.info(f"  Already exists: {os.path.basename(fname)}")
        return True

    # MEIDB form POST parameters (reverse-engineered from browser)
    payload = {
        "cmbPeriod":  str(year),
        "cmbMonth":   str(MONTH_MAP[month]),
        "cmbHS":      "4",          # HS 4-digit
        "Submit22":   "Get+Data",
    }

    try:
        r = session.post(
            f"{MEIDB_BASE}/commoditywise_exportq.asp",
            data=payload, timeout=30
        )
        if r.status_code == 200 and len(r.content) > 5000:
            with open(fname, "wb") as f:
                f.write(r.content)
            logger.info(f"  Saved: {os.path.basename(fname)} ({len(r.content)//1024}KB)")
            return True
        else:
            logger.warning(f"  Failed commodity export {month} {year}: HTTP {r.status_code}")
            return False
    except Exception as e:
        logger.warning(f"  Error commodity export {month} {year}: {e}")
        return False


def download_commodity_import(session, month: str, year: int, save_dir: str) -> bool:
    """Download commodity-wise import Excel for given month/year."""
    fname = os.path.join(save_dir, f"tradestat_commodity_import_{year}_{month}.xlsx")
    if os.path.exists(fname):
        logger.info(f"  Already exists: {os.path.basename(fname)}")
        return True

    payload = {
        "cmbPeriod":  str(year),
        "cmbMonth":   str(MONTH_MAP[month]),
        "cmbHS":      "4",
        "Submit22":   "Get+Data",
    }

    try:
        r = session.post(
            f"{MEIDB_BASE}/commoditywise_importq.asp",
            data=payload, timeout=30
        )
        if r.status_code == 200 and len(r.content) > 5000:
            with open(fname, "wb") as f:
                f.write(r.content)
            logger.info(f"  Saved: {os.path.basename(fname)} ({len(r.content)//1024}KB)")
            return True
        else:
            logger.warning(f"  Failed commodity import {month} {year}: HTTP {r.status_code}")
            return False
    except Exception as e:
        logger.warning(f"  Error: {e}")
        return False


def download_country_export(session, month: str, year: int, save_dir: str) -> bool:
    """Download country-wise export (total all commodities) for given month/year."""
    fname = os.path.join(save_dir, f"tradestat_country_export_{year}_{month}.xlsx")
    if os.path.exists(fname):
        logger.info(f"  Already exists: {os.path.basename(fname)}")
        return True

    payload = {
        "cmbPeriod":  str(year),
        "cmbMonth":   str(MONTH_MAP[month]),
        "cmbCountry": "0",   # All countries
        "Submit22":   "Get+Data",
    }

    try:
        r = session.post(
            f"{MEIDB_BASE}/countrywise_exportq.asp",
            data=payload, timeout=30
        )
        if r.status_code == 200 and len(r.content) > 5000:
            with open(fname, "wb") as f:
                f.write(r.content)
            logger.info(f"  Saved: {os.path.basename(fname)} ({len(r.content)//1024}KB)")
            return True
        else:
            logger.warning(f"  Failed country export {month} {year}: HTTP {r.status_code}")
            return False
    except Exception as e:
        logger.warning(f"  Error: {e}")
        return False


def download_country_import(session, month: str, year: int, save_dir: str) -> bool:
    """Download country-wise import for given month/year."""
    fname = os.path.join(save_dir, f"tradestat_country_import_{year}_{month}.xlsx")
    if os.path.exists(fname):
        logger.info(f"  Already exists: {os.path.basename(fname)}")
        return True

    payload = {
        "cmbPeriod":  str(year),
        "cmbMonth":   str(MONTH_MAP[month]),
        "cmbCountry": "0",
        "Submit22":   "Get+Data",
    }

    try:
        r = session.post(
            f"{MEIDB_BASE}/countrywise_importq.asp",
            data=payload, timeout=30
        )
        if r.status_code == 200 and len(r.content) > 5000:
            with open(fname, "wb") as f:
                f.write(r.content)
            logger.info(f"  Saved: {os.path.basename(fname)}")
            return True
        else:
            logger.warning(f"  Failed country import {month} {year}: HTTP {r.status_code}")
            return False
    except Exception as e:
        logger.warning(f"  Error: {e}")
        return False


def download_cxc_country(session, month: str, year: int,
                          country: str, flow: str, save_dir: str) -> bool:
    """
    Download CXC (commodity x country) file for one country.
    This is the key file — all HS4 codes for one specific country.
    """
    fname = os.path.join(save_dir,
                         f"tradestat_cxc_{flow}_{year}_{month}_{country}.xlsx")
    if os.path.exists(fname):
        return True  # Skip silently if exists

    flow_param = "export" if flow == "export" else "import"
    endpoint   = f"cxc_{flow_param}q.asp"

    payload = {
        "cmbPeriod":  str(year),
        "cmbMonth":   str(MONTH_MAP[month]),
        "cmbCountry": country,
        "cmbHS":      "4",
        "Submit22":   "Get+Data",
    }

    try:
        r = session.post(
            f"{MEIDB_BASE}/{endpoint}",
            data=payload, timeout=30
        )
        if r.status_code == 200 and len(r.content) > 3000:
            with open(fname, "wb") as f:
                f.write(r.content)
            return True
        return False
    except Exception:
        return False


# ── Step 3: Selenium fallback (if POST fails) ─────────────────────────────────

def download_via_selenium(month: str, year: int, save_dir: str):
    """
    Fallback: use Selenium to click through the tradestat forms.
    Only used if direct HTTP POST fails.
    
    Install: pip install selenium webdriver-manager
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select, WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        logger.error("Selenium not installed. Run: pip install selenium webdriver-manager")
        return

    logger.info(f"Starting Selenium for {month} {year} ...")

    opts = Options()
    opts.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(save_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    })
    # Uncomment next line to run without visible browser:
    # opts.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts
    )

    try:
        # CXC Export page
        driver.get(f"{MEIDB_BASE}/country_wise_all_commodities_export")
        time.sleep(3)

        wait = WebDriverWait(driver, 10)

        # Select year
        try:
            yr_sel = Select(wait.until(EC.presence_of_element_located(
                (By.NAME, "cmbPeriod")
            )))
            yr_sel.select_by_value(str(year))
        except Exception:
            logger.warning("Could not select year — page structure may have changed")

        # Select month
        try:
            mo_sel = Select(driver.find_element(By.NAME, "cmbMonth"))
            mo_sel.select_by_value(str(MONTH_MAP[month]))
        except Exception:
            logger.warning("Could not select month")

        # Click download/get data
        try:
            btn = driver.find_element(By.NAME, "Submit22")
            btn.click()
            time.sleep(5)
            logger.info("Selenium: clicked Get Data")
        except Exception as e:
            logger.warning(f"Button click failed: {e}")

    finally:
        driver.quit()


# ── Main orchestrator ─────────────────────────────────────────────────────────

def download_month(month: str, year: int, save_dir: str,
                   countries: list, delay: float = 1.0):
    """Download all file types for one month."""
    logger.info(f"\n{'='*55}")
    logger.info(f"  Downloading: {month} {year}")
    logger.info(f"{'='*55}")

    os.makedirs(save_dir, exist_ok=True)
    session = _get_session()
    results = {"success": 0, "failed": 0, "skipped": 0}

    # 1. Commodity files (2 files: export + import)
    logger.info(f"\n[1/3] Commodity files ...")
    for flow_fn in [download_commodity_export, download_commodity_import]:
        ok = flow_fn(session, month, year, save_dir)
        results["success" if ok else "failed"] += 1
        time.sleep(delay)

    # 2. Country totals (2 files: export + import)
    logger.info(f"\n[2/3] Country total files ...")
    for flow_fn in [download_country_export, download_country_import]:
        ok = flow_fn(session, month, year, save_dir)
        results["success" if ok else "failed"] += 1
        time.sleep(delay)

    # 3. CXC files (country × flow — the main data)
    logger.info(f"\n[3/3] CXC files ({len(countries)} countries x 2 flows) ...")
    total_cxc = len(countries) * 2
    done_cxc  = 0

    for country in countries:
        for flow in ["export", "import"]:
            ok = download_cxc_country(session, month, year, country, flow, save_dir)
            done_cxc += 1
            if ok:
                results["success"] += 1
            else:
                results["failed"] += 1

            if done_cxc % 10 == 0:
                logger.info(f"  CXC progress: {done_cxc}/{total_cxc}")
            time.sleep(delay / 2)

    logger.info(f"\nMonth {month} {year} done:")
    logger.info(f"  Success: {results['success']} | Failed: {results['failed']}")
    return results


def run_download(months: list, year: int = 2026,
                 countries: list = None, delay: float = 1.0):
    """Main download run."""
    if countries is None:
        countries = COUNTRIES

    os.makedirs(SAVE_DIR, exist_ok=True)
    total_success = 0
    total_failed  = 0

    print(f"\n{'='*60}")
    print(f"  TRADESTAT 2026 DATA DOWNLOADER")
    print(f"  Year     : {year}")
    print(f"  Months   : {months}")
    print(f"  Countries: {len(countries)}")
    print(f"  Save to  : {SAVE_DIR}")
    print(f"{'='*60}\n")

    for month in months:
        if month not in MONTH_MAP:
            logger.warning(f"Invalid month: {month} — skipping")
            continue

        results = download_month(month, year, SAVE_DIR, countries, delay)
        total_success += results["success"]
        total_failed  += results["failed"]

    print(f"\n{'='*60}")
    print(f"  DOWNLOAD COMPLETE")
    print(f"  Total success : {total_success}")
    print(f"  Total failed  : {total_failed}")
    print(f"\n  If failures > 0: tradestat may have blocked the requests.")
    print(f"  Solution: run with --selenium flag for browser automation.")
    print(f"\n  Next step: python main.py --process")
    print(f"  This adds 2026 data to your database and dashboard.")
    print(f"{'='*60}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download 2026 trade data from tradestat.commerce.gov.in",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_2026.py                        Download all available 2026 months
  python download_2026.py --months Jan           Download Jan 2026 only
  python download_2026.py --months Jan Feb       Download Jan and Feb 2026
  python download_2026.py --check                Check what months are available
  python download_2026.py --year 2025 --months Dec  Re-download Dec 2025

After download:
  python main.py --process    Add to database + update Excel + dashboard
        """
    )
    parser.add_argument("--months", nargs="+", default=None,
                        help="Months to download (Jan Feb Mar ...)")
    parser.add_argument("--year",   type=int, default=2026)
    parser.add_argument("--check",  action="store_true",
                        help="Check which months are available")
    parser.add_argument("--delay",  type=float, default=1.0,
                        help="Delay between requests in seconds (default 1.0)")
    parser.add_argument("--selenium", action="store_true",
                        help="Use Selenium browser automation instead of direct HTTP")
    parser.add_argument("--countries", nargs="+", default=None,
                        help="Specific countries to download (default: all)")
    args = parser.parse_args()

    if args.check:
        avail = check_available_months(args.year)
        print(f"\nAvailable months for {args.year}: {avail}\n")
        sys.exit(0)

    # Determine which months to download
    if args.months:
        months = [m.capitalize() for m in args.months]
    else:
        # Auto: download all months up to current month
        current_month = datetime.now().month
        months = [m for m, n in MONTH_MAP.items() if n <= current_month]
        if args.year < datetime.now().year:
            months = list(MONTH_MAP.keys())  # All months for past years

    countries = args.countries if args.countries else COUNTRIES

    if args.selenium:
        for month in months:
            download_via_selenium(month, args.year, SAVE_DIR)
    else:
        run_download(months, args.year, countries, args.delay)
