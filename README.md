# HRIA — Fișă de pontaj (Anexa 1)

> [!WARNING]
> **Unofficial and incomplete.** This is a personal, work-in-progress tool. It
> is not affiliated with or endorsed by HRIA, UVT, MFE, or PoCIDIF, and the
> files it produces are **not** official, complete, or legally valid documents.
> Always check the output against the official instruction and template before
> use.

A small web app for the **HRIA** project that fills in the **Anexa 1** timesheet
(`Fișă individuală pontaj`) required to claim salary costs, as set out by the
PoCIDIF instruction:

> **Instrucțiunea nr. 13/20.02.2026** privind decontarea cheltuielilor salariale
> solicitate prin cereri de rambursare/plată de beneficiarii proiectelor finanțate
> · [announcement](https://mfe.gov.ro/pocidif-instructiunea-nr-13-20-02-2026-privind-decontarea-cheltuielilor-salariale-solicitate-prin-cereri-de-rambursare-plata-de-beneficiarii-proiectelor-finantate/)
> · [PDF](https://mfe.gov.ro/wp-content/uploads/2026/02/2e8272b2ca3cb73ec1b856fed4ebc45e.pdf)
> · [Anexa (Excel)](https://mfe.gov.ro/wp-content/uploads/2026/02/f404e65335070b6de3ddf6ec0b66d0ad.xlsx)

It renders the official template from a simple form, so the monthly timesheets
can be produced quickly and consistently.

## What it does

- Fill in personal details and up to 12 contracts; the first is the main job (**NB**).
- Remembers the personal and contract details in your browser between visits.
- Enter daily time intervals — hours are computed and validated automatically
  (max 12 h/day, no overlaps, per-project max hours).
- Weekends are disabled; weekends and Romanian public holidays are highlighted.
- Exports a document that keeps the official template's formatting and formulas.

## Run

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run uvicorn app:app --reload   # http://127.0.0.1:8000
```

Deploys to [Render](https://render.com) via the included `render.yaml`.

## License

MIT for code, CC0-1.0 for configuration and data — see `REUSE.toml`.
