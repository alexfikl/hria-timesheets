// SPDX-FileCopyrightText: 2026 Alexandru Fikl <alexfikl@gmail.com>
// SPDX-License-Identifier: MIT

// Client-side helpers: hours from intervals, per-day limits/overlaps, rates.
// The server recomputes and re-validates everything authoritatively; these
// mirror the same rules for instant feedback and to disable the generate button.
(function () {
  const DAILY_LIMIT = 12;
  const RATES = [
    ["expert senior", 33.36],
    ["expert junior", 23.51],
  ];
  const EURO_TO_RON = 4.9765;

  const RANGE_PATTERN = "(\\d{1,2}):(\\d{2})\\s*-\\s*(\\d{1,2}):(\\d{2})";

  function parseNumber(text) {
    const value = parseFloat(String(text).replace(",", "."));
    return isNaN(value) ? null : value;
  }

  function sumHours(ranges) {
    return ranges.reduce(function (total, r) {
      return total + (r[1] - r[0]) / 60;
    }, 0);
  }

  // Returns [] for empty, null for malformed, or a list of [start, end] minutes.
  function parseRanges(text) {
    const trimmed = (text || "").trim();
    if (!trimmed) return [];
    const re = new RegExp(RANGE_PATTERN, "g");
    const ranges = [];
    let found = false;
    let match;
    while ((match = re.exec(trimmed)) !== null) {
      const sh = Number(match[1]);
      const sm = Number(match[2]);
      const eh = Number(match[3]);
      const em = Number(match[4]);
      if (sh > 24 || eh > 24 || sm > 59 || em > 59) return null;
      const start = sh * 60 + sm;
      const end = eh * 60 + em;
      if (end <= start) return null;
      ranges.push([start, end]);
      found = true;
    }
    const leftover = trimmed
      .replace(new RegExp(RANGE_PATTERN, "g"), "")
      .replace(/[\s,;]+/g, "");
    if (leftover || !found) return null;
    return ranges;
  }

  function fmt(value) {
    return String(Math.round(value * 100) / 100);
  }

  function hoursCell(name) {
    return document.querySelector('td[data-hours-for="' + name + '"]');
  }

  function refreshTotal() {
    let sum = 0;
    document.querySelectorAll("td.hours").forEach(function (td) {
      const value = parseFloat(td.textContent);
      if (!isNaN(value)) sum += value;
    });
    const el = document.getElementById("grand-total");
    if (el) el.textContent = String(Math.round(sum * 100) / 100);
  }

  function refreshIssues(errors) {
    const el = document.getElementById("live-issues");
    if (!el) return;
    if (errors.length) {
      el.hidden = false;
      el.textContent = errors.join("\n");
    } else {
      el.hidden = true;
      el.textContent = "";
    }
  }

  function setGenerateEnabled(enabled) {
    const button = document.querySelector("button.primary");
    if (button) button.disabled = !enabled;
  }

  function syncProjectHeaders() {
    document.querySelectorAll('input[name^="project_"]').forEach(function (input) {
      const index = input.name.replace("project_", "");
      const header = document.querySelector(
        'th[data-project-header="' + index + '"]'
      );
      if (!header) return;
      if (index === "0") {
        header.textContent = "Norma de Bază";
        return;
      }
      const name = input.value.trim();
      header.textContent = name || "Proiect " + (Number(index) + 1);
    });
  }

  function validateAll() {
    const errors = [];
    let badFormat = 0;

    // 1. Format each interval and recompute its hours cell.
    document.querySelectorAll('input[name^="interval_"]').forEach(function (input) {
      input.classList.remove("invalid");
      const ranges = parseRanges(input.value);
      const cell = hoursCell(input.name);
      if (ranges === null) {
        badFormat += 1;
        input.classList.add("invalid");
        if (cell) {
          cell.textContent = "?";
          cell.classList.add("invalid");
        }
      } else if (cell) {
        cell.textContent = fmt(sumHours(ranges));
        cell.classList.remove("invalid");
      }
    });

    if (badFormat > 0) {
      errors.push(
        badFormat === 1
          ? "1 interval are format invalid."
          : badFormat + " intervale au format invalid."
      );
    }

    // 2. Per day: total hours and overlapping intervals.
    document.querySelectorAll("tr[data-day]").forEach(function (row) {
      row.classList.remove("over");
      const day = row.getAttribute("data-day");
      let total = 0;
      let overlap = false;
      const ranges = [];
      row.querySelectorAll('input[name^="interval_"]').forEach(function (input) {
        const parsed = parseRanges(input.value);
        if (parsed === null) return;
        parsed.forEach(function (r) {
          total += (r[1] - r[0]) / 60;
          ranges.push({ start: r[0], end: r[1], input: input });
        });
      });

      for (let i = 0; i < ranges.length; i++) {
        for (let j = i + 1; j < ranges.length; j++) {
          if (ranges[i].start < ranges[j].end && ranges[j].start < ranges[i].end) {
            ranges[i].input.classList.add("invalid");
            ranges[j].input.classList.add("invalid");
            overlap = true;
          }
        }
      }

      const over = total > DAILY_LIMIT + 1e-9;
      if (over) row.classList.add("over");
      if (over) {
        errors.push(
          "Ziua " + day + ": " + fmt(total) +
          " h depășesc limita de " + DAILY_LIMIT + " h."
        );
      }
      if (overlap) errors.push("Ziua " + day + ": intervale orare suprapuse.");
    });

    // 3. Non-NB projects: max hours must be filled and must not be exceeded.
    document.querySelectorAll('input[name^="max_hours_"]').forEach(function (input) {
      input.classList.remove("invalid");
    });
    const projectTotals = {};
    document.querySelectorAll('input[name^="interval_"]').forEach(function (input) {
      const match = input.name.match(/^interval_\d+_(\d+)$/);
      if (!match) return;
      const parsed = parseRanges(input.value);
      if (parsed === null) return;
      const index = Number(match[1]);
      projectTotals[index] = (projectTotals[index] || 0) + sumHours(parsed);
    });
    document.querySelectorAll('input[name^="max_hours_"]').forEach(function (input) {
      const index = Number(input.name.replace("max_hours_", ""));
      const value = parseNumber(input.value);
      const total = projectTotals[index] || 0;
      if (value === null || value <= 0) {
        input.classList.add("invalid");
        errors.push("Proiect " + (index + 1) + ": completați orele maxime.");
      } else if (total > value + 1e-9) {
        input.classList.add("invalid");
        errors.push(
          "Proiect " + (index + 1) + ": " + fmt(total) +
          " h depășesc maximul de " + fmt(value) + " h."
        );
      }
    });

    refreshIssues(errors);
    refreshTotal();
    setGenerateEnabled(errors.length === 0);
  }

  function syncRon() {
    const euro = document.querySelector('input[name="euro_rate"]');
    const ron = document.querySelector('input[name="ron_rate"]');
    if (!euro || !ron) return;
    const value = parseNumber(euro.value);
    ron.value = value === null ? "" : String(Math.round(value * EURO_TO_RON));
  }

  function applyFunctionRate() {
    const field = document.querySelector('input[name="function"]');
    const euro = document.querySelector('input[name="euro_rate"]');
    if (!field || !euro) return;
    const text = field.value.trim().toLowerCase();
    for (const [key, rate] of RATES) {
      if (text.includes(key)) {
        euro.value = rate.toFixed(2);
        break;
      }
    }
    syncRon();
  }

  document.addEventListener("input", function (event) {
    const input = event.target;
    if (input.matches('input[name^="interval_"]')) {
      validateAll();
      return;
    }
    if (input.name === "function") {
      applyFunctionRate();
      return;
    }
    if (input.name === "euro_rate") {
      syncRon();
      return;
    }
    if (input.name && input.name.indexOf("project_") === 0) {
      syncProjectHeaders();
    }
  });

  function refreshAll() {
    validateAll();
    syncProjectHeaders();
  }

  document.addEventListener("htmx:afterSwap", refreshAll);
  document.addEventListener("DOMContentLoaded", refreshAll);
})();
