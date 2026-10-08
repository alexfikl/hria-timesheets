# SPDX-FileCopyrightText: 2026 Alexandru Fikl <alexfikl@gmail.com>
# SPDX-License-Identifier: MIT

"""Build a blank, 31-day Anexa 1 template from the official filled file.

The official file has only 30 day rows (rows 14-43), a total row (44) and a
footer (45-58). Since months can have 31 days we insert a 31st day row and shift
the total + footer down. openpyxl's insert_rows() does not move styles or merged
ranges, so we do the shift manually and deterministically.

All footer rows are merged across B:I and only their column B holds content, so
the footer shift only needs to move column B and the merged ranges.

Run once:

    python tools/build_template.py <source.xlsx> templates/anexa1_blank.xlsx
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import openpyxl
from openpyxl.cell.cell import Cell
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

COLS = range(2, 10)  # B..I
DAY_FIRST_ROW = 14
DAY_LAST_ROW = 43  # day 30
TOTAL_ROW = 44
FOOTER_FIRST_ROW = 45
FOOTER_LAST_ROW = 58


def _copy_style(src: Cell, dst: Cell) -> None:
    dst._style = copy.copy(src._style)


def _move_cell(src: Cell, dst: Cell) -> None:
    _copy_style(src, dst)
    dst.value = src.value


def build(src_path: Path, out_path: Path) -> None:
    wb = openpyxl.load_workbook(src_path)
    ws = wb["Pontaj"]

    # 1. Unmerge the whole footer block, then re-merge it shifted down by one.
    #    Doing it in two passes avoids overlap between old and new ranges.
    footer_merges = [
        m
        for m in ws.merged_cells.ranges
        if FOOTER_FIRST_ROW <= m.min_row and m.max_row <= FOOTER_LAST_ROW
    ]
    for merged in footer_merges:
        ws.unmerge_cells(str(merged))
    for merged in footer_merges:
        ws.merge_cells(
            start_row=merged.min_row + 1,
            start_column=merged.min_col,
            end_row=merged.max_row + 1,
            end_column=merged.max_col,
        )

    # 2. Shift footer content down. Footer rows are merged B:I, so only the
    #    top-left column B carries content/style.
    for row in range(FOOTER_LAST_ROW, FOOTER_FIRST_ROW - 1, -1):
        _move_cell(ws.cell(row, 2), ws.cell(row + 1, 2))
        height = ws.row_dimensions[row].height
        if height is not None:
            ws.row_dimensions[row + 1].height = height

    # 3. Shift the (now unmerged) total row 44 -> 45.
    for col in COLS:
        _move_cell(ws.cell(TOTAL_ROW, col), ws.cell(TOTAL_ROW + 1, col))
    total_height = ws.row_dimensions[TOTAL_ROW].height
    if total_height is not None:
        ws.row_dimensions[TOTAL_ROW + 1].height = total_height

    # 4. Turn row 44 into day 31, copying day 30's formatting.
    for col in COLS:
        _copy_style(ws.cell(DAY_LAST_ROW, col), ws.cell(DAY_LAST_ROW + 1, col))
    ws.cell(DAY_LAST_ROW + 1, 2).value = 31
    ws.row_dimensions[DAY_LAST_ROW + 1].height = ws.row_dimensions[DAY_LAST_ROW].height

    # 5. Scrub personal / example data left over from the source file.
    for coord in ("B4", "F6", "F7", "F8", "F9", "F10", "F11", "C12", "E12", "G12"):
        ws[coord] = None

    # 6. Day rows: keep day numbers, clear hours/intervals/fills, refresh totals.
    #    The source file highlights weekends in column B with a fixed orange,
    #    which is only correct for its own month - strip it; the app recolours.
    no_fill = PatternFill(fill_type=None)
    new_last_day = DAY_LAST_ROW + 1  # 44
    for row in range(DAY_FIRST_ROW, new_last_day + 1):
        for col in range(3, 10):  # C..I
            ws.cell(row, col).value = None
        for col in COLS:
            ws.cell(row, col).fill = no_fill
        ws.cell(row, 9).value = f"=SUM(C{row},E{row},G{row})"

    # 7. Totals row (now 45) gets fresh formulas over 31 days.
    total_row = new_last_day + 1  # 45
    for col in (3, 5, 7, 9):
        letter = get_column_letter(col)
        ws.cell(
            total_row, col
        ).value = f"=SUM({letter}{DAY_FIRST_ROW}:{letter}{new_last_day})"

    # 8. Footer personal data (shifted coordinates).
    ws["B47"] = None  # "Numele si prenumele persoana: ..."
    ws["B49"] = None  # date
    ws["B51"] = None  # leader
    ws["B53"] = "=B49"  # repair shifted formula

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(sys.argv[2]))
