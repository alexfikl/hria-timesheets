# Generator fișă de pontaj — Anexa 1

Small FastAPI web app that fills the official Romanian **Anexa 1** timesheet
(`Fișă individuală pontaj`) from a simple form: personal details, any number of
contracts/grant projects (contract #1 is always the main job, **NB**), and daily
time intervals.

## Features

- Separate **family name** and **given name**; the output is always normalised to
  `FAMILY Given` (family uppercased, given title-cased).
- Identification fields laid out as: name (family + given), CNP, function, then
  euro + RON rate. The **leader/partner is a fixed constant**
  (`Prof. Dr. Viorel NEGRU`), not an input.
- **Any number of contracts** (1–12, set with a number spinner). The contract
  table is resized per request to fit exactly the projects entered.
- Contract #1 is always the **Norma de Bază (NB)** main job.
- Each contract stores its **CIM/act number** and an optional **project acronym**.
  The header row always includes
  `Contract Individual de Muncă/Act administrativ de numire. Nr. <number> (<project>)`
  and appends ` (NB)` to the first (main) contract.
- Every **non-NB** contract also has a required **monthly max hours** field. It
  must be filled in, and the project's total hours may not exceed it (both are
  errors that gray out the Generate button and block the file). The NB contract
  has no max.
- Editable day grid: enter **only the intervals** — the `Ore` column is computed
  automatically, both live in the browser and authoritatively on the server.
- Grid column headers show **Norma de Bază** for the main job and each project's
  acronym (falling back to `Proiect N` when blank); they update as you type.
- Intervals may be non-contiguous, e.g. `8:00-12:00; 16:00-20:00`. A malformed
  interval turns its field (and the computed hours cell) **red** live, with a
  summary message.
- **Weekends cannot be filled** (inputs disabled and ignored server-side).
  Public holidays stay editable but are highlighted.
- Validation errors (and the **Generate button is grayed out** until they are
  fixed): **max 12 h/day**, malformed intervals, and **overlapping intervals**
  (between projects, or within one interval list). The server re-checks all of
  them and refuses to produce the file on any error.
- `Zi` column uses two-letter weekdays (`Lu Ma Mi Jo Vi Sâ Du`); weekends and
  Romanian public holidays are colour-highlighted and described in a tooltip.
- Gray-highlighting is a checkbox.
- The euro/RON rate is prefilled from the function (`Expert senior` → 33.36 €,
  `Expert junior` → 23.51 €); RON = `euro × 4.9765`, **rounded to the nearest
  integer**.
- Fills a copy of the official template, preserving its formatting, merges and
  formulas.
- No telemetry, no sign-in, no frontend build step.

## Local run

Install [uv](https://docs.astral.sh/uv/), then:

```bash
uv sync
uv run uvicorn app:app --reload
```

Open <http://127.0.0.1:8000>.

## Deploy on Render

1. Push this folder to a Git repository.
2. Create a **Web Service**; Render reads `render.yaml` and uses uv automatically
   (a `uv.lock` is committed):
   - Build: `uv sync --frozen --no-dev`
   - Start: `uv run --no-dev uvicorn app:app --host 0.0.0.0 --port $PORT`

## Project layout

```
app.py                       FastAPI routes
web/forms.py                 form -> Timesheet + template context (pure, testable)
web/templates/index.html     full page (Jinja2 + a little HTMX)
web/templates/_workspace.html  project inputs + day grid (HTMX partial)
web/static/app.js            live hours calculation
web/static/styles.css        styling
timesheet/intervals.py       parse/format "8:00-12:00; 16:00-20:00"
timesheet/holidays.py        Romanian public holidays + weekdays
timesheet/model.py           data model + validation rules
timesheet/layout.py          resize the contract columns to the number of projects
timesheet/template.py        fill the Anexa 1 template
tools/build_template.py      rebuild templates/anexa1_blank.xlsx
templates/anexa1_blank.xlsx  blanked 31-day, 3-contract base template
```

HTMX is vendored locally in `web/static/htmx.min.js` and used only as progressive
enhancement (updating the grid when the month or contract count changes). The app
works without it; the grid simply refreshes when the form is submitted.

## Security

- Text written into the workbook is stored as literal strings, so a value
  starting with `=` cannot become an Excel formula (formula injection).
- HTMX is served from our own `/static`, not a third-party CDN.
- Every response sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer` and a restrictive `Content-Security-Policy`.
- Dependencies are locked in `uv.lock` and installed with uv.
- The app stores nothing and form bodies are not logged.

## Notes / limitations

- The UI allows up to 12 contracts. The sheet grows to fit; there is no hard
  architectural ceiling, only the number in `MAX_CONTRACTS` (`timesheet/model.py`).
- `templates/anexa1_blank.xlsx` is generated from the official file with all
  personal data removed, and is **required at runtime**. The `.gitignore`
  ignores `*.xlsx` but force-includes this file — make sure it is committed.
- Romanian holidays are computed for 1900–2099. If you need other countries,
  add a calendar module.
- Importing `pontaj_*.xlsx` is a planned next step, not implemented yet.
