# Innovation Portfolio Dashboard

A premium, fully dynamic web dashboard for the Innovation Tracker, replacing
the original Tkinter desktop app. Python (Flask + pandas) owns all data
processing; the browser front end delivers the polished, interactive
experience — filters, charts, tables and a project detail view all update
live from your Excel file.

## What's inside

```
innovation-dashboard/
├── app.py                 Flask app + REST API
├── data_loader.py         Excel reading, column normalisation, KPIs/status logic
├── requirements.txt
├── run.bat                 One-click Windows launcher
├── data/
│   └── Innovations_Updated.xlsx   <- your live data file (replace/update this)
├── images/                 Drop project photos here later (see below)
├── static/
│   ├── css/style.css
│   ├── js/app.js
│   └── js/vendor/chart.min.js     Chart.js, bundled locally (no internet needed)
└── templates/
    └── index.html
```

## Running it (Windows, no internet required after setup)

1. Install [Python 3.10+](https://www.python.org/downloads/) if it isn't
   already on the machine (tick "Add Python to PATH" during install — this
   is the only step that needs internet, and only if Python isn't already
   installed).
2. Double-click **`run.bat`**. It installs Flask/pandas/openpyxl straight
   into your Python (no virtual environment, nothing to get out of sync)
   and starts the server. First run takes under a minute; every run after
   that is instant since the packages are already there.
3. Your browser opens automatically at `http://127.0.0.1:5057`.

To stop the dashboard, close the console window `run.bat` opened.

If `run.bat` reports an error, the console window will stay open and show
it in red — copy that text if you need help, it tells you exactly what
went wrong (missing Python, blocked internet access for pip, etc).

### Running manually (Mac/Linux/dev machine)

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5057`.

## Updating the data

Replace `data/Innovations_Updated.xlsx` with your latest export (keep the
same filename), then click **Refresh Data** in the dashboard header. The
app re-reads the sheet, recalculates every KPI/chart/table, and updates the
"Last updated" indicator — no restart needed.

The loader is tolerant of the usual messiness in a hand-maintained tracker:
it matches column headers even if spacing/typos vary slightly (e.g.
`Desciption`, `Yr- 26`), treats blank/`TBD`/`N/A` cells as "no data" rather
than erroring, and simply ignores any columns it doesn't recognise. If you
add new categories, brands, projects or statuses, they appear automatically
— nothing is hard-coded.

Recognised status values are grouped into: **On Track**, **Landed**,
**Delayed**, **Kick-off**, and **TBD** (anything else, or a blank cell,
falls back to TBD).

## Adding project images later

Drop an image into `images/` named after the project's
**Category-Brand-Project** slug (lowercase, spaces → hyphens), e.g. a
project "SSK Natural 205ml" under Hair/Sunsilk would be:

```
images/hair-sunsilk-ssk-natural-205ml.jpg
```

Supported formats: `.jpg`, `.jpeg`, `.png`, `.webp`. If no matching image
exists, the project detail view shows a clean placeholder — nothing breaks.
(Open a project's detail panel and check the browser's network tab, or ask
for a small script, if you want the exact slug for a tricky project name.)

## Packaging for another computer

The simplest option is to zip the whole `innovation-dashboard` folder
(everything is self-contained, no cloud services or external APIs are
called) and copy it across, then run `run.bat` on the target machine.

If you'd like a single `.exe` with no visible Python install, this project
can be built with PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" --add-data "data;data" app.py
```

(Ask if you'd like this pre-built and wired up — it's a small follow-up.)

## API reference (for future extension)

| Endpoint                  | Method | Purpose                                          |
|----------------------------|--------|---------------------------------------------------|
| `/api/dashboard`           | GET    | KPIs, charts, filter options, and table for the current filter/search state (query params: `category`, `brand`, `project`, `status`, `year`, `q`) |
| `/api/project/<id>`        | GET    | Full detail record for one project                |
| `/api/risks`               | GET    | Projects with a non-empty Risks field, respecting active filters |
| `/api/refresh`             | POST   | Re-reads the Excel file from disk                  |
| `/api/image/<filename>`    | GET    | Serves a project image from `images/`              |

Everything is JSON, so the same API can power a future mobile view, exports,
or another frontend without touching the data layer.
