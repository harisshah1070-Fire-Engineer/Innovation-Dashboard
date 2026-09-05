"""
Innovation Portfolio Dashboard
-------------------------------
Local Flask application. Python owns all data processing (Excel reading,
normalisation, filtering, KPI + chart aggregation); the frontend is a static,
richly interactive single-page app that talks to this API over JSON.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5057 in a browser.
"""

from __future__ import annotations

import os
from collections import Counter, OrderedDict

from flask import Flask, jsonify, request, send_from_directory, send_file

from data_loader import (
    store, STATUS_ORDER, STATUS_META, CATEGORY_PALETTE, FIELD_LABELS,
    PROJECT_CARD_FIELDS, IMAGES_DIR,
)

app = Flask(__name__, static_folder="static", template_folder="templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_param(name: str) -> list[str]:
    """Read a repeatable / comma-separated query param into a clean list."""
    vals = request.args.getlist(name)
    out: list[str] = []
    for v in vals:
        out.extend(p for p in v.split(",") if p.strip())
    return [v.strip() for v in out if v.strip()]


def _active_filters() -> dict:
    return {
        "categories": _split_param("category"),
        "brands": _split_param("brand"),
        "projects": _split_param("project"),
        "statuses": _split_param("status"),
        "years": _split_param("year"),
        "search": request.args.get("q", "").strip(),
    }


def _color_for_category(cat: str, all_categories: list[str]) -> str:
    idx = all_categories.index(cat) if cat in all_categories else 0
    return CATEGORY_PALETTE[idx % len(CATEGORY_PALETTE)]


def _kpis(records: list[dict]) -> dict:
    total = len(records)
    counts = Counter(r["status"] for r in records)
    at_risk = sum(1 for r in records if r["has_risk"] and r["status"] not in ("Landed",))
    categories = {r["category"] for r in records}
    brands = {r["brand"] for r in records}
    return {
        "total_projects": total,
        "on_track": counts.get("On Track", 0),
        "delayed": counts.get("Delayed", 0),
        "landed": counts.get("Landed", 0),
        "kick_off": counts.get("Kick-off", 0),
        "tbd": counts.get("TBD", 0),
        "at_risk": at_risk,
        "categories": len(categories),
        "brands": len(brands),
    }


def _charts(records: list[dict]) -> dict:
    all_categories = sorted({r["category"] for r in store.records})

    by_category_counter = Counter(r["category"] for r in records)
    by_category = [
        {"label": cat, "value": n, "color": _color_for_category(cat, all_categories)}
        for cat, n in sorted(by_category_counter.items(), key=lambda kv: -kv[1])
    ]

    by_brand_counter = Counter(r["brand"] for r in records)
    by_brand = [
        {"label": b, "value": n}
        for b, n in sorted(by_brand_counter.items(), key=lambda kv: -kv[1])
    ]

    by_status_counter = Counter(r["status"] for r in records)
    by_status = [
        {"label": s, "value": by_status_counter.get(s, 0), "color": STATUS_META[s]["color"]}
        for s in STATUS_ORDER
        if by_status_counter.get(s, 0) > 0
    ]

    # progress summary keeps a stable order/zero-filled, handy for a bar chart
    progress = [
        {"label": s, "value": by_status_counter.get(s, 0), "color": STATUS_META[s]["color"]}
        for s in STATUS_ORDER
    ]

    return {
        "by_category": by_category,
        "by_brand": by_brand,
        "by_status": by_status,
        "progress": progress,
    }


def _filter_options(active: dict) -> dict:
    all_records = store.records

    def opts(key: str, upstream: list[dict]) -> list[str]:
        return sorted({r[key] for r in upstream if r.get(key)})

    categories = opts("category", all_records)

    recs_for_brand = store.filtered(categories=active["categories"])
    brands = opts("brand", recs_for_brand)

    recs_for_project = store.filtered(categories=active["categories"], brands=active["brands"])
    projects = sorted({r["project"] for r in recs_for_project if r.get("project")})

    statuses = [s for s in STATUS_ORDER if any(r["status"] == s for r in all_records)]
    years = sorted({str(r["yr"]) for r in all_records if r.get("yr")})

    return {
        "categories": categories,
        "brands": brands,
        "projects": projects,
        "statuses": statuses,
        "years": years,
    }


def _table_row(r: dict) -> dict:
    return {
        "id": r["id"],
        "category": r["category"],
        "brand": r["brand"],
        "project": r["project"],
        "site": r.get("site"),
        "status": r["status"],
        "trial_status": r.get("trial_status"),
        "yr": r.get("yr"),
        "gm": r.get("gm"),
        "has_risk": r["has_risk"],
    }


def _project_detail(r: dict) -> dict:
    cards = []
    for field in PROJECT_CARD_FIELDS:
        cards.append({
            "field": field,
            "label": FIELD_LABELS.get(field, field.title()),
            "value": r.get(field),
        })
    return {
        "id": r["id"],
        "category": r["category"],
        "brand": r["brand"],
        "project": r["project"],
        "status": r["status"],
        "status_meta": STATUS_META.get(r["status"], STATUS_META["TBD"]),
        "site": r.get("site"),
        "scope": r.get("scope"),
        "description": r.get("description"),
        "risks": r.get("risks"),
        "updates": r.get("updates"),
        "has_risk": r["has_risk"],
        "image_url": r.get("image_url"),
        "cards": cards,
        "slug": r["slug"],
    }


# ---------------------------------------------------------------------------
# Routes: frontend
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_file(os.path.join(app.template_folder, "index.html"))


# ---------------------------------------------------------------------------
# Routes: API
# ---------------------------------------------------------------------------

@app.route("/api/dashboard")
def api_dashboard():
    active = _active_filters()
    records = store.filtered(
        categories=active["categories"],
        brands=active["brands"],
        projects=active["projects"],
        statuses=active["statuses"],
        years=active["years"],
        search=active["search"],
    )
    return jsonify({
        "kpis": _kpis(records),
        "charts": _charts(records),
        "filters": _filter_options(active),
        "table": [_table_row(r) for r in records],
        "count": len(records),
        "total_in_source": len(store.records),
        "last_updated": store.last_updated,
        "last_loaded_at": store.last_loaded_at,
        "source_missing": store.source_missing,
        "status_meta": STATUS_META,
    })


@app.route("/api/project/<int:record_id>")
def api_project(record_id: int):
    r = store.get(record_id)
    if r is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(_project_detail(r))


@app.route("/api/risks")
def api_risks():
    active = _active_filters()
    records = store.filtered(
        categories=active["categories"],
        brands=active["brands"],
        projects=active["projects"],
        statuses=active["statuses"],
        years=active["years"],
        search=active["search"],
    )
    risky = [r for r in records if r["has_risk"]]
    out = [{
        "id": r["id"],
        "category": r["category"],
        "brand": r["brand"],
        "project": r["project"],
        "status": r["status"],
        "risks": r.get("risks"),
        "updates": r.get("updates"),
    } for r in risky]
    return jsonify({"risks": out, "count": len(out)})


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    store.load()
    return jsonify({
        "success": not store.source_missing,
        "last_updated": store.last_updated,
        "last_loaded_at": store.last_loaded_at,
        "source_missing": store.source_missing,
        "total_records": len(store.records),
    })


@app.route("/api/image/<path:filename>")
def api_image(filename: str):
    if not os.path.isdir(IMAGES_DIR):
        return jsonify({"error": "no images directory"}), 404
    return send_from_directory(IMAGES_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5057))
    print(f"\nInnovation Portfolio Dashboard running at http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
