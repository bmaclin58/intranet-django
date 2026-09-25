# CalCloud local demo

Open **http://127.0.0.1:8001/calcloud/** after running `run_calcloud.py` from the repository root. In PyCharm, select the project's `.venv` interpreter and press Run; no arguments are needed. Change `HOST` and `PORT` at the top of that script if necessary. The development server defaults to localhost.

From PowerShell at the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_calcloud.py
```

This app has no database models, migrations, login requirement, or connection to CalCloud records. The existing helpdesk homepage and account routes remain in place.

## Pages and data

Dashboard, Assets, Asset Tracker (introduction, search, and records), Recalls, Help, and ChangeLog are under `/calcloud/`. Details are read-only. Contact, Shop, the PDF guide, and video resources open the original websites. Those destinations may require their own login.

`demo_data.py` contains deterministic fixtures: 1,590 assets, 28 tracking records, and 712 changes. Supplied example rows are retained; the remaining records, instrument associations, and chart history are synthetic. The 782 active / 808 inactive classifications and health counts (32 Current, 14 Due, 278 Overdue, 22 In Process) are explicit demo classifications, not inferred CalCloud business rules. Dates are frozen so the demo does not change with today's date. The 292 recalls comprise Due and Overdue demo assets.

Every table uses AG Grid Community 36.2.0. Column menus provide text/date filters, headers sort, column edges resize, and wide tables scroll horizontally. Filters combine; date bounds are inclusive and exclude missing dates. CSV export includes every filtered, sorted record across all pages and excludes action buttons. Missing dates display as N/A. Identifiers remain strings; when opening a CSV in a spreadsheet, import identifier columns as text to preserve leading zeroes. Formula-like text is escaped during export.

The demo omits edits, certificates, service submissions, authentication, purchasing, Enterprise grouping, Excel export, and tool panels. No frontend build or external CDN is required at runtime.

## Files and dependencies

- `urls.py`, `views.py`: namespaced routes, page context, record lookup.
- `demo_data.py`: fixture definitions and derived totals.
- `templates/CalCloud/`: shared layout and page templates; data uses Django `json_script`.
- `static/CalCloud/portal.js`, `portal.css`: shared grids, filters, dialogs, charts, responsive layout.
- `static/CalCloud/vendor/`: pinned AG Grid browser bundle and MIT license, from `https://unpkg.com/ag-grid-community@36.2.0/dist/ag-grid-community.min.js` and the same package's `LICENSE.txt`.
- `static/CalCloud/logo.png`: reference logo from `https://calcloud.standardcal.com/assets/logo-15632fec.png`; CalCloud branding belongs to its owner.
- Lato Regular/Bold/Black reuse `helpdesk/static/helpdesk/`; Light is stored locally from `https://fonts.gstatic.com/s/lato/v24/S6u9w4BMUTPHh7USSwiPGQ.woff2`. Lato uses SIL OFL 1.1; see `static/CalCloud/Lato-OFL.txt`.
- Chart.js 4.4.0 reuses `unfold/js/chart/chart.js`, including its bundled MIT license. WhiteNoise is now declared in root requirements because project settings already reference it.

## Verification

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test CalCloud
node CalCloud/portal.test.cjs
```

Four Django tests cover public routes, fixture counts and associations, valid/missing tracking records, safe JSON, and local assets. The Node check covers combined filters, date boundaries, missing values, identifiers, and CSV escaping.

Browser checks covered desktop (1920px), laptop (1366px), mobile (390px), navigation, summary filters, empty/reset states, pagination/page sizes, dialogs and restored focus, keyboard Help tabs, and console errors. A downloaded 14-row CSV was checked against the full filtered fixture in descending order, including the second grid page. Recall and ChangeLog export actions were also exercised.

The broader existing helpdesk suite currently has 3 failures and 12 errors involving submissions/uploads (21 tests). The same results reproduced with CalCloud disabled and the original URL configuration; those unrelated failures are not changed here.
