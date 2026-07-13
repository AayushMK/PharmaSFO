/* Nepali (Bikram Sambat) date picker.
 *
 * A field that opens a mini BS month-calendar popup (like the native date
 * picker, but in BS). Picking a day writes the ISO **AD** date to an
 * underlying hidden input — forms, sync handlers, and the server keep
 * speaking Gregorian.
 *
 * Needs the BS month table embedded by the `bs_calendar_json` template tag:
 *   <script id="bs-cal-data" type="application/json">[...]</script>
 *
 * Usage:
 *   - Server-rendered `<input type="date">` elements are auto-enhanced on load.
 *   - JS-created rows call `bsDateAttach(input, { defaultToday: true })`.
 */
(function () {
  "use strict";

  var MONTH_NAMES = ["Baishakh", "Jestha", "Asar", "Shrawan", "Bhadau", "Aswin",
                     "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra"];
  var DOW = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
  var DAY_MS = 86400000;
  var CAL = [];

  function loadCal() {
    if (CAL.length) return true;
    var el = document.getElementById("bs-cal-data");
    if (!el) return false;
    try { CAL = JSON.parse(el.textContent); } catch (e) { CAL = []; }
    return CAL.length > 0;
  }

  function rec(y, m) {
    for (var i = 0; i < CAL.length; i++) {
      if (CAL[i].y === y && CAL[i].m === m) return CAL[i];
    }
    return null;
  }

  function adToBs(iso) {
    var t = Date.parse(iso + "T00:00:00Z");
    if (isNaN(t)) return null;
    for (var i = 0; i < CAL.length; i++) {
      var diff = Math.round((t - Date.parse(CAL[i].start + "T00:00:00Z")) / DAY_MS);
      if (diff >= 0 && diff < CAL[i].days) return { y: CAL[i].y, m: CAL[i].m, d: diff + 1 };
    }
    return null;
  }

  function bsToAd(y, m, d) {
    var r = rec(y, m);
    if (!r) return "";
    return new Date(Date.parse(r.start + "T00:00:00Z") + (d - 1) * DAY_MS)
      .toISOString().slice(0, 10);
  }

  function todayIso() {
    var now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString().slice(0, 10);
  }

  function fmt(bs) { return bs.d + " " + MONTH_NAMES[bs.m - 1] + " " + bs.y; }

  var STYLES = "" +
    ".bs-date-wrap{position:relative;width:100%;max-width:240px}" +
    ".bs-date-trigger{display:flex;align-items:center;justify-content:space-between;gap:var(--space-2);cursor:pointer;text-align:left}" +
    ".bs-date-trigger .bs-placeholder{color:var(--text-muted)}" +
    ".bs-date-panel{position:absolute;top:calc(100% + 4px);left:0;z-index:40;width:256px;" +
      "background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);" +
      "box-shadow:var(--shadow-modal);padding:var(--space-3)}" +
    ".bs-date-panel[hidden]{display:none}" +
    ".bs-date-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-top:var(--space-2)}" +
    ".bs-date-grid .bs-dow{font-size:var(--text-xs);font-weight:var(--weight-semibold);color:var(--text-muted);" +
      "text-align:center;padding:2px 0;text-transform:uppercase;letter-spacing:var(--tracking-label)}" +
    ".bs-day{height:30px;border:none;background:none;border-radius:var(--radius-sm);font-family:inherit;" +
      "font-size:var(--text-sm);color:var(--text);cursor:pointer}" +
    ".bs-day:hover{background:var(--gray-100)}" +
    ".bs-day.is-today{box-shadow:inset 0 0 0 1px var(--primary);color:var(--primary)}" +
    ".bs-day.is-selected{background:var(--primary);color:#fff;font-weight:var(--weight-semibold)}";

  function injectStyles() {
    if (document.getElementById("bs-date-styles")) return;
    var s = document.createElement("style");
    s.id = "bs-date-styles";
    s.textContent = STYLES;
    document.head.appendChild(s);
  }

  function closeAllPanels() {
    document.querySelectorAll(".bs-date-panel:not([hidden])").forEach(function (p) {
      p.hidden = true;
    });
  }

  window.bsDateAttach = function (input, opts) {
    opts = opts || {};
    if (!loadCal() || input.dataset.bsAttached) return;
    input.dataset.bsAttached = "1";
    input.type = "hidden";
    injectStyles();

    var selected = input.value ? adToBs(input.value) : null;
    if (!selected && opts.defaultToday) selected = adToBs(todayIso());
    var todayBs = adToBs(todayIso());
    var view = selected ? { y: selected.y, m: selected.m }
                        : (todayBs ? { y: todayBs.y, m: todayBs.m } : { y: CAL[0].y, m: CAL[0].m });

    var wrap = document.createElement("div");
    wrap.className = "bs-date-wrap";
    wrap.innerHTML =
      '<button type="button" class="input bs-date-trigger">' +
        '<span class="bs-value bs-placeholder">Select date</span>' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;flex:none;color:var(--text-muted)"><rect x="3" y="4" width="18" height="17" rx="1.5"/><path d="M3 9h18M8 2v4M16 2v4"/></svg>' +
      '</button>' +
      '<div class="bs-date-panel" hidden>' +
        '<div class="row row--between">' +
          '<button type="button" class="btn btn--ghost btn--icon btn--sm bs-prev" aria-label="Previous month"><svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M15 6l-6 6 6 6"/></svg></button>' +
          '<strong class="bs-title" style="font-size:var(--text-base)"></strong>' +
          '<button type="button" class="btn btn--ghost btn--icon btn--sm bs-next" aria-label="Next month"><svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg></button>' +
        '</div>' +
        '<div class="bs-date-grid"></div>' +
      '</div>';
    input.parentNode.insertBefore(wrap, input);

    var trigger = wrap.querySelector(".bs-date-trigger");
    var valueEl = wrap.querySelector(".bs-value");
    var panel = wrap.querySelector(".bs-date-panel");
    var title = wrap.querySelector(".bs-title");
    var grid = wrap.querySelector(".bs-date-grid");
    var prevBtn = wrap.querySelector(".bs-prev");
    var nextBtn = wrap.querySelector(".bs-next");

    function showValue() {
      if (selected) {
        valueEl.textContent = fmt(selected);
        valueEl.classList.remove("bs-placeholder");
      } else {
        valueEl.textContent = "Select date";
        valueEl.classList.add("bs-placeholder");
      }
    }

    function setValue(bs) {
      selected = bs;
      showValue();
      var iso = bs ? bsToAd(bs.y, bs.m, bs.d) : "";
      if (input.value !== iso) {
        input.value = iso;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }

    function shift(delta) {
      var y = view.y, m = view.m + delta;
      if (m < 1) { m = 12; y -= 1; }
      if (m > 12) { m = 1; y += 1; }
      if (!rec(y, m)) return;
      view = { y: y, m: m };
      renderMonth();
    }

    function renderMonth() {
      var r = rec(view.y, view.m);
      if (!r) return;
      title.textContent = MONTH_NAMES[view.m - 1] + " " + view.y;
      prevBtn.disabled = !rec(view.m === 1 ? view.y - 1 : view.y, view.m === 1 ? 12 : view.m - 1);
      nextBtn.disabled = !rec(view.m === 12 ? view.y + 1 : view.y, view.m === 12 ? 1 : view.m + 1);

      grid.innerHTML = "";
      DOW.forEach(function (d) {
        var s = document.createElement("span");
        s.className = "bs-dow";
        s.textContent = d;
        grid.appendChild(s);
      });
      var startCol = new Date(r.start + "T00:00:00Z").getUTCDay(); // 0 = Sunday
      for (var b = 0; b < startCol; b++) grid.appendChild(document.createElement("span"));
      for (var d = 1; d <= r.days; d++) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "bs-day";
        btn.textContent = d;
        if (todayBs && view.y === todayBs.y && view.m === todayBs.m && d === todayBs.d) btn.classList.add("is-today");
        if (selected && view.y === selected.y && view.m === selected.m && d === selected.d) btn.classList.add("is-selected");
        btn.dataset.day = d;
        grid.appendChild(btn);
      }
    }

    grid.addEventListener("click", function (e) {
      var b = e.target.closest(".bs-day");
      if (!b) return;
      setValue({ y: view.y, m: view.m, d: Number(b.dataset.day) });
      panel.hidden = true;
    });
    prevBtn.addEventListener("click", function () { shift(-1); });
    nextBtn.addEventListener("click", function () { shift(1); });
    trigger.addEventListener("click", function () {
      var open = panel.hidden;
      closeAllPanels();
      if (open) {
        view = selected ? { y: selected.y, m: selected.m } : view;
        renderMonth();
        panel.hidden = false;
      }
    });
    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) panel.hidden = true;
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") panel.hidden = true;
    });

    if (selected) setValue(selected); else showValue();
    renderMonth();
  };

  // Progressive enhancement: convert every server-rendered date input.
  document.addEventListener("DOMContentLoaded", function () {
    if (!loadCal()) return;
    document.querySelectorAll('input[type="date"]').forEach(function (el) {
      window.bsDateAttach(el);
    });
  });
})();
