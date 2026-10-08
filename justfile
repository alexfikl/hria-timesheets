PYTHON := 'python'
PY_SOURCES := 'app.py timesheet web tools'
BLANK_TEMPLATE := 'templates/anexa1_blank.xlsx'

HTMX_VERSION := '2'
HTMX_OUT := 'web/static/htmx.min.js'

_default:
    @just --list

# {{{ formatting

alias fmt: format

[doc('Reformat all source code')]
format: isort black pyproject justfmt

[doc('Run ruff isort fixes over the source code')]
isort:
    ruff check --fix --select=I {{ PY_SOURCES }}
    ruff check --fix --select=RUF022 {{ PY_SOURCES }}
    @echo -e "\e[1;32mruff isort clean!\e[0m"

[doc('Run ruff format over the source code')]
black:
    ruff format {{ PY_SOURCES }}
    @echo -e "\e[1;32mruff format clean!\e[0m"

[doc('Run pyproject-fmt over the configuration')]
pyproject:
    {{ PYTHON }} -m pyproject_fmt --indent 4 --max-supported-python '3.12' pyproject.toml
    @echo -e "\e[1;32mpyproject clean!\e[0m"

[doc('Run just --fmt over the justfile')]
justfmt:
    just --unstable --fmt
    @echo -e "\e[1;32mjust --fmt clean!\e[0m"

# }}}
# {{{ linting

[doc('Run all linting checks over the source code')]
lint: typos reuse ruff ty

[doc('Run typos over the source code and documentation')]
typos:
    typos --sort
    @echo -e "\e[1;32mtypos clean!\e[0m"

[doc('Check REUSE license compliance')]
reuse:
    {{ PYTHON }} -m reuse lint
    @echo -e "\e[1;32mREUSE compliant!\e[0m"

[doc('Run ruff checks over the source code')]
ruff:
    ruff check {{ PY_SOURCES }}
    @echo -e "\e[1;32mruff clean!\e[0m"

[doc('Run ty checks over the source code')]
ty:
    ty check {{ PY_SOURCES }}
    @echo -e "\e[1;32mty clean!\e[0m"

# }}}
# {{{ lock

[doc('Update uv.lock')]
lock:
    uv lock

[doc('Sync the environment from uv.lock')]
sync:
    uv sync

# }}}
# {{{ assets

[doc('Regenerate the blank Anexa 1 template')]
template source:
    {{ PYTHON }} tools/build_template.py '{{ source }}' {{ BLANK_TEMPLATE }}
    @echo "\e[1;32mTemplate regenerated: {{ BLANK_TEMPLATE }}\e[0m"

[doc('Download the latest HTMX into web/static')]
htmx version=HTMX_VERSION:
    curl -fsSL 'https://unpkg.com/htmx.org@{{ version }}/dist/htmx.min.js' -o {{ HTMX_OUT }}
    @echo "\e[1;32mHTMX @{{ version }} downloaded: {{ HTMX_OUT }}\e[0m"

# }}}
# {{{ run

[doc('Run the app locally (uvicorn --reload)')]
run *args:
    {{ PYTHON }} -m uvicorn app:app --reload {{ args }}

# }}}
