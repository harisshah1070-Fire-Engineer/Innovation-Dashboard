"""
data_loader.py
----------------
Handles everything related to reading `Innovations Updated.xlsx`, normalising
column names/values, and turning the raw sheet into clean, JSON-serialisable
structures the Flask API can hand to the frontend.

Designed to be tolerant of the messiness that's typical of a hand-maintained
tracker: renamed columns, stray whitespace, blended date/text cells, "TBD"
placeholders, blank rows, etc. Nothing here is hard-coded to specific
projects/brands/categories -- everything is derived from whatever is in the
sheet at load time.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import threading
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
EXCEL_FILENAME = "Innovations_Updated.xlsx"
EXCEL_PATH = os.path.join(DATA_DIR, EXCEL_FILENAME)
SHEET_NAME = "Innovation Tracker Updated"

# Canonical field -> list of acceptable raw header variants (normalised: lower,
# stripped, internal whitespace collapsed, punctuation-insensitive).
COLUMN_ALIASES: dict[str, list[str]] = {
    "category": ["category"],
    "brand": ["brand"],
    "project": ["project"],
    "scope": ["scope"],
    "description": ["description", "desciption", "descripton"],
    "gm": ["gm", "gm%", "gm percent"],
    "ito_mn": ["ito(mn)", "ito mn", "ito"],
    "yr": ["yr", "year"],
    "dp_vol": ["dp vol", "dpvol", "dp volume"],
    "yr_26": ["yr 26", "yr26", "yr-26"],
    "first_fy": ["1st fy", "first fy", "1stfy"],
    "sku_format": ["sku format", "sku & format", "sku and format"],
    "trial_status": ["trial status"],
    "site": ["site"],
    "stability": ["stability"],
    "production": ["production"],
    "primaries": ["primaries"],
    "risks": ["risks", "risk"],
    "updates": ["updates", "update"],
    "status": ["status"],
}

# Friendly display labels for the frontend (used for card titles, etc.)
FIELD_LABELS: dict[str, str] = {
    "scope": "Scope",
    "description": "Description",
    "gm": "GM",
    "ito_mn": "iTO (mn)",
    "yr": "Year",
    "dp_vol": "DP Vol",
    "yr_26": "Yr-26",
    "first_fy": "1st FY",
    "sku_format": "SKU & Format",
    "trial_status": "Trial Status",
    "site": "Site",
    "stability": "Stability",
    "production": "Production",
    "primaries": "Primaries",
}

# Order in which project-info cards should be displayed.
PROJECT_CARD_FIELDS = [
    "scope", "gm", "ito_mn", "yr", "dp_vol", "yr_26", "first_fy",
    "sku_format", "trial_status", "site", "stability", "production",
    "primaries",
]

STATUS_CANON = {
    "on track": "On Track",
    "on-track": "On Track",
    "landed": "Landed",
    "done": "Landed",
    "completed": "Landed",
    "delayed": "Delayed",
    "kick off": "Kick-off",
    "kick-off": "Kick-off",
    "kickoff": "Kick-off",
    "tbd": "TBD",
    "not started": "TBD",
}

STATUS_ORDER = ["On Track", "Kick-off", "Delayed", "Landed", "TBD"]

STATUS_META = {
    "On Track":  {"color": "#1F9D6C", "bg": "#E4F7ED", "key": "on_track"},
    "Landed":    {"color": "#2F6FED", "bg": "#E8EFFE", "key": "landed"},
    "Delayed":   {"color": "#E4483A", "bg": "#FDEAE8", "key": "delayed"},
    "Kick-off":  {"color": "#C7871A", "bg": "#FBF0DD", "key": "kick_off"},
    "TBD":       {"color": "#6B7280", "bg": "#EEF0F3", "key": "tbd"},
}

CATEGORY_PALETTE = [
    "#0F6E5D", "#C7871A", "#2F6FED", "#A6446E", "#3F7D5C", "#8452C2",
    "#B0542A", "#1A8FA6",
]

_norm_re = re.compile(r"[^a-z0-9]+")


def _norm_key(s: str) -> str:
    return _norm_re.sub(" ", str(s).lower()).strip()


# Reverse lookup: normalised raw header -> canonical field
_ALIAS_LOOKUP: dict[str, str] = {}
for canon, variants in COLUMN_ALIASES.items():
    for v in variants:
        _ALIAS_LOOKUP[_norm_key(v)] = canon


def _clean_scalar(val: Any) -> Any:
    """Turn a raw pandas cell into a clean, JSON-friendly python value."""
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    if isinstance(val, str):
        s = val.strip()
        if s == "" or s.lower() in ("nan", "none", "n/a", "na"):
            return None
        return s
    if isinstance(val, (pd.Timestamp, dt.datetime, dt.date)):
        try:
            return pd.Timestamp(val).strftime("%d %b %Y")
        except Exception:
            return str(val)
    if isinstance(val, float):
        if val.is_integer():
            return int(val)
        return round(val, 3)
    return val


def _slugify(*parts: str) -> str:
    s = "-".join(str(p) for p in parts if p)
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


class DataStore:
    """Thread-safe holder for the currently-loaded dataset."""

    def __init__(self, excel_path: str = EXCEL_PATH, sheet_name: str = SHEET_NAME):
        self.excel_path = excel_path
        self.sheet_name = sheet_name
        self._lock = threading.Lock()
        self.records: list[dict[str, Any]] = []
        self.last_updated: str | None = None
        self.last_loaded_at: str | None = None
        self.source_missing = False
        self.load()

    # -- loading -----------------------------------------------------------

    def load(self) -> None:
        with self._lock:
            if not os.path.exists(self.excel_path):
                self.records = []
                self.source_missing = True
                self.last_loaded_at = dt.datetime.now().strftime("%d %b %Y, %H:%M")
                return

            self.source_missing = False
            try:
                df = pd.read_excel(self.excel_path, sheet_name=self.sheet_name)
            except Exception:
                # fall back to first sheet if the named one isn't found
                df = pd.read_excel(self.excel_path, sheet_name=0)

            df = self._normalise_columns(df)
            records = self._build_records(df)
            self.records = records

            try:
                mtime = os.path.getmtime(self.excel_path)
                self.last_updated = dt.datetime.fromtimestamp(mtime).strftime("%d %b %Y, %H:%M")
            except Exception:
                self.last_updated = dt.datetime.now().strftime("%d %b %Y, %H:%M")
            self.last_loaded_at = dt.datetime.now().strftime("%d %b %Y, %H:%M")

    def _normalise_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {}
        for col in df.columns:
            key = _norm_key(col)
            canon = _ALIAS_LOOKUP.get(key)
            if canon:
                rename_map[col] = canon
        df = df.rename(columns=rename_map)

        # Ensure every canonical field exists even if missing from the sheet.
        for canon in COLUMN_ALIASES:
            if canon not in df.columns:
                df[canon] = None

        # Drop fully blank rows (no category/brand/project at all).
        core = ["category", "brand", "project"]
        df = df.dropna(how="all", subset=core)
        return df

    def _build_records(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        records = []
        rid = 0
        for _, row in df.iterrows():
            category = _clean_scalar(row.get("category"))
            brand = _clean_scalar(row.get("brand"))
            project = _clean_scalar(row.get("project"))

            # Skip rows with no meaningful project identity.
            if not (category or brand or project):
                continue

            raw_status = _clean_scalar(row.get("status"))
            status = self._canon_status(raw_status)

            rec: dict[str, Any] = {
                "id": rid,
                "category": category or "Uncategorised",
                "brand": brand or "Unspecified",
                "project": project or "Untitled Project",
                "status": status,
                "status_raw": raw_status,
            }
            for field in COLUMN_ALIASES:
                if field in ("category", "brand", "project", "status"):
                    continue
                rec[field] = _clean_scalar(row.get(field))

            rec["has_risk"] = bool(rec.get("risks"))
            rec["slug"] = _slugify(rec["category"], rec["brand"], rec["project"])
            rec["image_url"] = self._find_image(rec["slug"])
            records.append(rec)
            rid += 1
        return records

    @staticmethod
    def _canon_status(raw: Any) -> str:
        if not raw:
            return "TBD"
        key = _norm_key(raw)
        return STATUS_CANON.get(key, "TBD" if key == "tbd" else str(raw).strip().title())

    @staticmethod
    def _find_image(slug: str) -> str | None:
        if not os.path.isdir(IMAGES_DIR):
            return None
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            candidate = os.path.join(IMAGES_DIR, slug + ext)
            if os.path.exists(candidate):
                return f"/api/image/{slug}{ext}"
        return None

    # -- query helpers -------------------------------------------------------

    def filtered(
        self,
        categories: list[str] | None = None,
        brands: list[str] | None = None,
        projects: list[str] | None = None,
        statuses: list[str] | None = None,
        years: list[str] | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        recs = self.records
        if categories:
            cset = set(categories)
            recs = [r for r in recs if r["category"] in cset]
        if brands:
            bset = set(brands)
            recs = [r for r in recs if r["brand"] in bset]
        if projects:
            pset = set(projects)
            recs = [r for r in recs if r["project"] in pset]
        if statuses:
            sset = set(statuses)
            recs = [r for r in recs if r["status"] in sset]
        if years:
            yset = {str(y) for y in years}
            recs = [r for r in recs if str(r.get("yr")) in yset]
        if search:
            q = search.strip().lower()
            if q:
                recs = [
                    r for r in recs
                    if q in str(r.get("project", "")).lower()
                    or q in str(r.get("brand", "")).lower()
                    or q in str(r.get("category", "")).lower()
                ]
        return recs

    def get(self, record_id: int) -> dict[str, Any] | None:
        for r in self.records:
            if r["id"] == record_id:
                return r
        return None


store = DataStore()
