/* Month picker — grid popover with year steppers.
 *
 * Replaces native `<input type="month">`, which hides year selection behind
 * an unsignposted scroll list in Chrome and renders as a bare text box in
 * Firefox/desktop Safari. The trigger opens a panel with a ‹ year › header,
 * a 4×3 month grid, and a "This month" shortcut; picking a month writes
 * "YYYY-MM" to the underlying (hidden) input, so forms and the server see
 * exactly what the native control submitted.
 *
 * Usage:
 *   - Server-rendered `<input type="month">` elements are auto-enhanced on load.
 *   - JS-created inputs call `monthPickerAttach(input)`.
 */
(function () {
  "use strict";

  var MONTHS = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"];
  var ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  var STYLES = "" +
    ".mp-wrap{position:relative;display:inline-block}" +
    ".mp-trigger{display:flex;align-items:center;justify-content:space-between;gap:var(--space-2);" +
      "cursor:pointer;text-align:left;width:180px}" +
    ".mp-trigger .mp-caret{width:16px;height:16px;color:var(--text-muted);flex:none}" +
    ".mp-panel{position:absolute;top:calc(100% + 4px);left:0;z-index:40;width:256px;" +
      "background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);" +
      "box-shadow:var(--shadow-modal);padding:var(--space-3)}" +
    ".mp-panel[hidden]{display:none}" +
    ".mp-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-2)}" +
    ".mp-year{font-size:var(--text-base);font-weight:var(--weight-semibold)}" +
    ".mp-nav{display:grid;place-items:center;width:28px;height:28px;border:none;background:none;" +
      "border-radius:var(--radius-sm);color:var(--text-secondary);cursor:pointer}" +
    ".mp-nav:hover{background:var(--gray-100);color:var(--text)}" +
    ".mp-nav svg{width:16px;height:16px}" +
    ".mp-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:4px}" +
    ".mp-mon{height:32px;border:none;background:none;border-radius:var(--radius-sm);" +
      "font-family:inherit;font-size:var(--text-sm);color:var(--text);cursor:pointer}" +
    ".mp-mon:hover{background:var(--gray-100)}" +
    ".mp-mon.is-now{box-shadow:inset 0 0 0 1px var(--primary);color:var(--primary)}" +
    ".mp-mon.is-selected{background:var(--primary);color:#fff;font-weight:var(--weight-semibold)}" +
    ".mp-foot{display:flex;justify-content:flex-end;margin-top:var(--space-2);" +
      "padding-top:var(--space-2);border-top:1px solid var(--border)}" +
    ".mp-today{border:none;background:none;font-family:inherit;font-size:var(--text-sm);" +
      "color:var(--primary);font-weight:var(--weight-medium);cursor:pointer;" +
      "padding:var(--space-1) var(--space-2);border-radius:var(--radius-sm)}" +
    ".mp-today:hover{background:var(--primary-tint)}";

  function injectStyles() {
    if (document.getElementById("mp-styles")) return;
    var s = document.createElement("style");
    s.id = "mp-styles";
    s.textContent = STYLES;
    document.head.appendChild(s);
  }

  function closeAll() {
    document.querySelectorAll(".mp-panel:not([hidden])").forEach(function (p) {
      p.hidden = true;
      var t = p.parentNode.querySelector(".mp-trigger");
      if (t) t.setAttribute("aria-expanded", "false");
    });
  }

  function parseYM(v) {
    var m = /^(\d{4})-(\d{2})$/.exec(v || "");
    if (!m) return null;
    var mon = parseInt(m[2], 10);
    if (mon < 1 || mon > 12) return null;
    return { y: parseInt(m[1], 10), m: mon };
  }

  function nowYM() {
    var d = new Date();
    return { y: d.getFullYear(), m: d.getMonth() + 1 };
  }

  function fmtYM(sel) {
    return sel.y + "-" + (sel.m < 10 ? "0" : "") + sel.m;
  }

  window.monthPickerAttach = function (input) {
    if (input.dataset.mpAttached) return;
    input.dataset.mpAttached = "1";
    injectStyles();

    var sel = parseYM(input.value) || nowYM();
    var view = sel.y;                       // year currently shown in the panel
    var today = nowYM();

    input.type = "hidden";
    input.value = fmtYM(sel);

    var wrap = document.createElement("div");
    wrap.className = "mp-wrap";

    var trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "input mp-trigger";
    trigger.setAttribute("aria-haspopup", "true");
    trigger.setAttribute("aria-expanded", "false");
    if (input.id) trigger.id = input.id + "-trigger";
    if (input.style.width) trigger.style.width = input.style.width;
    trigger.innerHTML = '<span class="mp-label"></span>' +
      '<svg class="mp-caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>';
    var label = trigger.querySelector(".mp-label");

    var panel = document.createElement("div");
    panel.className = "mp-panel";
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Choose month");
    panel.innerHTML =
      '<div class="mp-head">' +
        '<button type="button" class="mp-nav" data-step="-1" aria-label="Previous year">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg></button>' +
        '<span class="mp-year"></span>' +
        '<button type="button" class="mp-nav" data-step="1" aria-label="Next year">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg></button>' +
      '</div>' +
      '<div class="mp-grid"></div>' +
      '<div class="mp-foot"><button type="button" class="mp-today">This month</button></div>';
    var yearEl = panel.querySelector(".mp-year");
    var grid = panel.querySelector(".mp-grid");

    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    wrap.appendChild(trigger);
    wrap.appendChild(panel);

    // Point the field's <label> at the trigger so clicking it opens the picker
    if (input.id) {
      var lab = document.querySelector('label[for="' + input.id + '"]');
      if (lab) lab.htmlFor = trigger.id;
    }

    function render() {
      label.textContent = MONTHS[sel.m - 1] + " " + sel.y;
      yearEl.textContent = view;
      grid.innerHTML = "";
      for (var m = 1; m <= 12; m++) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "mp-mon" +
          (view === today.y && m === today.m ? " is-now" : "") +
          (view === sel.y && m === sel.m ? " is-selected" : "");
        b.dataset.m = m;
        b.textContent = ABBR[m - 1];
        grid.appendChild(b);
      }
    }

    function pick(y, m) {
      sel = { y: y, m: m };
      input.value = fmtYM(sel);
      input.dispatchEvent(new Event("change", { bubbles: true }));
      render();
      closeAll();
      trigger.focus();
    }

    trigger.addEventListener("click", function () {
      var open = panel.hidden;
      closeAll();
      if (open) {
        view = sel.y;
        render();
        panel.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
      }
    });
    panel.querySelectorAll(".mp-nav").forEach(function (btn) {
      btn.addEventListener("click", function () {
        view += parseInt(btn.dataset.step, 10);
        render();
      });
    });
    grid.addEventListener("click", function (e) {
      var b = e.target.closest(".mp-mon");
      if (b) pick(view, parseInt(b.dataset.m, 10));
    });
    panel.querySelector(".mp-today").addEventListener("click", function () {
      today = nowYM();
      view = today.y;
      pick(today.y, today.m);
    });

    render();
  };

  document.addEventListener("click", function (e) {
    if (!e.target.closest(".mp-wrap")) closeAll();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeAll();
  });

  function enhanceAll() {
    document.querySelectorAll('input[type="month"]').forEach(function (el) {
      window.monthPickerAttach(el);
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceAll);
  } else {
    enhanceAll();
  }
})();
