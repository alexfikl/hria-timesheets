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
  // The reference rate lives on the server; it is rendered onto <body>.
  const EURO_TO_RON = parseFloat(document.body.dataset.euroToRon);

  const STORE_KEY = "hrtimesheets.form";
  const PERSIST_FIELD =
    /^(?:family_name|given_name|function|euro_rate|ron_rate|count|(?:contract|project|max_hours)_\d+)$/;
  const SAVED_INPUTS =
    'input[name^="contract_"], input[name^="project_"], input[name^="max_hours_"], ' +
    'input[name="family_name"], input[name="given_name"], ' +
    'input[name="function"], input[name="euro_rate"], input[name="ron_rate"]';

  const RANGE_RE = /(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})/g;

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
    RANGE_RE.lastIndex = 0;
    const ranges = [];
    let found = false;
    let match;
    while ((match = RANGE_RE.exec(trimmed)) !== null) {
      const sh = Number(match[1]);
      const sm = Number(match[2]);
      const eh = Number(match[3]);
      const em = Number(match[4]);
      if (
        sh > 24 ||
        eh > 24 ||
        sm > 59 ||
        em > 59 ||
        (sh === 24 && sm > 0) ||
        (eh === 24 && em > 0)
      ) {
        return null;
      }
      const start = sh * 60 + sm;
      const end = eh * 60 + em;
      if (end <= start) return null;
      ranges.push([start, end]);
      found = true;
    }
    const leftover = trimmed
      .replace(RANGE_RE, "")
      .replace(/[\s,;]+/g, "");
    if (leftover || !found) return null;
    ranges.sort(function (a, b) {
      return a[0] - b[0];
    });
    return ranges;
  }

  function fmt(value) {
    return String(Math.round(value * 100) / 100);
  }

  function hoursCell(input) {
    if (input && input.parentElement && input.parentElement.previousElementSibling) {
      return input.parentElement.previousElementSibling;
    }
    const name = typeof input === "string" ? input : (input && input.name);
    return document.querySelector('td[data-hours-for="' + name + '"]');
  }

  function refreshTotal(total) {
    const el = document.getElementById("grand-total");
    if (!el) return;
    if (typeof total === "number") {
      el.textContent = fmt(total);
      return;
    }
    let sum = 0;
    document.querySelectorAll("td.hours").forEach(function (td) {
      const value = parseFloat(td.textContent);
      if (!isNaN(value)) sum += value;
    });
    el.textContent = fmt(sum);
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
    const button = document.querySelector("#form button.primary");
    if (button) button.disabled = !enabled;
  }

  let cachedStore = null;
  let saveTimer = null;

  function loadStore() {
    if (cachedStore !== null) return cachedStore;
    try {
      cachedStore = JSON.parse(window.localStorage.getItem(STORE_KEY)) || {};
    } catch (err) {
      cachedStore = {};
    }
    if (cachedStore && cachedStore.cnp !== undefined) {
      delete cachedStore.cnp;
      saveStore(cachedStore);
    }
    return cachedStore;
  }

  function flushStore() {
    if (saveTimer !== null) {
      clearTimeout(saveTimer);
      saveTimer = null;
    }
    if (cachedStore !== null) {
      try {
        window.localStorage.setItem(STORE_KEY, JSON.stringify(cachedStore));
      } catch (err) {
        // storage may be unavailable (e.g. private mode); ignore
      }
    }
  }

  function saveStore(store) {
    cachedStore = store;
    if (saveTimer !== null) clearTimeout(saveTimer);
    saveTimer = setTimeout(flushStore, 250);
  }

  function persistField(input) {
    if (!input || !PERSIST_FIELD.test(input.name || "")) return;
    const store = loadStore();
    store[input.name] = input.value;
    saveStore(store);
  }

  // After a server-side import, overwrite the stored copy with the freshly
  // rendered values so restoreFields() cannot replace them with stale data.
  function persistImported() {
    const store = loadStore();
    document.querySelectorAll("input, select").forEach(function (input) {
      if (input.name && PERSIST_FIELD.test(input.name)) {
        store[input.name] = input.value;
      }
    });
    saveStore(store);
  }

  function restoreFields() {
    const store = loadStore();
    document.querySelectorAll(SAVED_INPUTS).forEach(function (input) {
      if (Object.prototype.hasOwnProperty.call(store, input.name)) {
        input.value = store[input.name];
      }
    });
  }

  function rerenderWorkspace() {
    const form = document.getElementById("form");
    if (window.fetch && form) {
      const params = new URLSearchParams();
      new FormData(form).forEach(function (value, key) {
        params.append(key, value);
      });
      window
        .fetch("/partial", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: params.toString(),
        })
        .then(function (response) {
          return response.ok ? response.text() : "";
        })
        .then(function (html) {
          const target = document.getElementById("workspace");
          if (!target || !html) return;
          target.outerHTML = html;
          refreshAll();
        })
        .catch(function () {
          // keep the page usable even if the refresh fails
        });
      return;
    }
    const count = document.querySelector('input[name="count"]');
    if (count) count.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function restoreCount() {
    const store = loadStore();
    const count = document.querySelector('input[name="count"]');
    if (!count || store["count"] === undefined) return;
    const desired = Number.parseInt(store["count"], 10);
    if (!Number.isFinite(desired) || desired < 1) return;
    if (count.value !== String(desired)) count.value = String(desired);
    // On reload the browser may have restored the count input value while the
    // server-rendered grid still has fewer project columns, so compare the
    // number of rendered panels rather than trusting the input's value.
    if (desired !== document.querySelectorAll("#workspace .project").length) {
      rerenderWorkspace();
    }
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
    let totalHours = 0;
    const parsedCache = new Map();

    // 1. Format each interval and recompute its hours cell.
    document.querySelectorAll('input[name^="interval_"]').forEach(function (input) {
      input.classList.remove("invalid");
      const ranges = parseRanges(input.value);
      parsedCache.set(input, ranges);
      const cell = hoursCell(input);
      if (ranges === null) {
        badFormat += 1;
        input.classList.add("invalid");
        if (cell) {
          cell.textContent = "?";
          cell.classList.add("invalid");
        }
      } else if (cell) {
        const hours = sumHours(ranges);
        totalHours += hours;
        cell.textContent = fmt(hours);
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
        const parsed = parsedCache.get(input);
        if (!parsed) return;
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
    parsedCache.forEach(function (parsed, input) {
      if (!parsed) return;
      const match = input.name.match(/^interval_\d+_(\d+)$/);
      if (!match) return;
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
    refreshTotal(totalHours);
    setGenerateEnabled(errors.length === 0);
  }

  function syncRon() {
    const euro = document.querySelector('input[name="euro_rate"]');
    const ron = document.querySelector('input[name="ron_rate"]');
    if (!euro || !ron || !Number.isFinite(EURO_TO_RON)) return;
    const value = parseNumber(euro.value);
    ron.value = value === null ? "" : String(Math.round(value * EURO_TO_RON));
    persistField(ron);
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
    persistField(euro);
    syncRon();
  }

  document.addEventListener("input", function (event) {
    const input = event.target;
    if (input.matches('input[name^="interval_"]')) {
      validateAll();
      return;
    }
    persistField(input);
    if (input.name === "function") {
      applyFunctionRate();
      return;
    }
    if (input.name === "euro_rate") {
      syncRon();
      return;
    }
    if ((input.name || "").startsWith("project_")) {
      syncProjectHeaders();
    }
  });

  function refreshAll() {
    if (document.body && document.body.dataset.imported === "1") {
      persistImported();
      document.body.removeAttribute("data-imported");
    }
    restoreFields();
    restoreCount();
    validateAll();
    syncProjectHeaders();
  }

  // Mirror the current form into the import request so uploaded values merge
  // with whatever is already filled in.
  function snapshotMainForm() {
    const form = document.getElementById("form");
    const target = document.getElementById("import-state");
    if (!form || !target) return;
    target.replaceChildren();
    new FormData(form).forEach(function (value, key) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = key;
      input.value = value;
      target.appendChild(input);
    });
  }

  const importForm = document.querySelector("form.import-form");
  if (importForm) importForm.addEventListener("submit", snapshotMainForm);

  const clearBtn = document.getElementById("clear-store");
  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      if (
        window.confirm(
          "Sigur doriți să ștergeți datele salvate din acest browser?"
        )
      ) {
        cachedStore = {};
        try {
          window.localStorage.removeItem(STORE_KEY);
        } catch (err) {}
        window.location.reload();
      }
    });
  }

  window.addEventListener("beforeunload", flushStore);
  document.addEventListener("htmx:afterSwap", refreshAll);
  document.addEventListener("DOMContentLoaded", refreshAll);
})();
