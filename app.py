"""FastAPI app that generates a Romanian "Anexa 1" timesheet.

Run locally with:

    uvicorn app:app --reload
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from timesheet.model import validate
from timesheet.template import render
from web.forms import build_context

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

app = FastAPI(title="Generator pontaj Anexa 1")
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "web" / "static")),
    name="static",
)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; "
        "script-src 'self'; connect-src 'self'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'"
    ),
}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    _timesheet, context = build_context({})
    return templates.TemplateResponse(request, "index.html", context)


@app.post("/partial", response_class=HTMLResponse)
async def partial(request: Request):
    """Re-render the project inputs + day grid for an HTMX swap."""
    form = await request.form()
    _timesheet, context = build_context(form)
    return templates.TemplateResponse(request, "_workspace.html", context)


@app.post("/generate")
async def generate(request: Request):
    form = await request.form()
    timesheet, context = build_context(form)

    issues = validate(timesheet)
    context["errors"] = [issue for issue in issues if issue.level == "error"]
    context["warnings"] = [issue for issue in issues if issue.level == "warning"]

    if context["errors"]:
        return templates.TemplateResponse(
            request, "index.html", context, status_code=422
        )

    data = render(timesheet, gray=context["gray"])
    safe_name = (
        re.sub(r"[^A-Za-z0-9]+", "_", timesheet.display_name).strip("_")
        or "Timesheet"
    )
    filename = f"{safe_name}_Timesheet_{context['month']:02d}_{context['year']}.xlsx"
    return Response(
        content=data,
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
