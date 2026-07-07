/* ==========================================================================
   Lumo SFA — behaviour helpers (vanilla JS, no dependencies)
   Progressive enhancement: everything degrades to a static page without JS.
   In Django, include with <script src="{% static 'lumo/lumo.js' %}" defer></script>
   ========================================================================== */
(function () {
  "use strict";

  /* ---- Collapsible sections (data-toggle="collapse", data-target="#id") ---- */
  document.addEventListener("click", function (e) {
    var trigger = e.target.closest('[data-toggle="collapse"]');
    if (!trigger) return;
    var group = trigger.closest("[data-collapsible]") ||
                document.querySelector(trigger.getAttribute("data-target"));
    if (!group) return;
    var collapsed = group.classList.toggle("is-collapsed");
    trigger.setAttribute("aria-expanded", String(!collapsed));
  });

  /* ---- Gallery accordion (data-accordion header buttons) ------------------ */
  document.querySelectorAll("[data-accordion-header]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var section = btn.closest("[data-accordion]");
      if (!section) return;
      var open = section.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", String(open));
    });
  });

  /* ---- Modals (data-open-modal="#id", [data-close-modal]) ----------------- */
  function openModal(sel) {
    var m = document.querySelector(sel);
    if (m) { m.hidden = false; document.body.style.overflow = "hidden"; }
  }
  function closeModal(m) {
    if (m) { m.hidden = true; document.body.style.overflow = ""; }
  }
  document.addEventListener("click", function (e) {
    var opener = e.target.closest("[data-open-modal]");
    if (opener) { openModal(opener.getAttribute("data-open-modal")); return; }

    var closer = e.target.closest("[data-close-modal]");
    if (closer) { closeModal(closer.closest(".modal-overlay")); return; }

    if (e.target.classList && e.target.classList.contains("modal-overlay")) {
      closeModal(e.target); // click on scrim
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay:not([hidden])").forEach(closeModal);
    }
  });

  /* ---- Toasts ------------------------------------------------------------- */
  function ensureStack() {
    var s = document.querySelector(".toast-stack");
    if (!s) { s = document.createElement("div"); s.className = "toast-stack"; document.body.appendChild(s); }
    return s;
  }
  var ICONS = {
    info:    '<path d="M12 8h.01M11 12h1v4h1"/><circle cx="12" cy="12" r="9"/>',
    success: '<circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>',
    warning: '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    danger:  '<circle cx="12" cy="12" r="9"/><path d="M15 9l-6 6M9 9l6 6"/>'
  };
  window.lumoToast = function (opts) {
    opts = opts || {};
    var type = opts.type || "info";
    var stack = ensureStack();
    var el = document.createElement("div");
    el.className = "toast toast--" + type;
    el.setAttribute("role", "status");
    el.innerHTML =
      '<svg class="toast__icon ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + (ICONS[type] || ICONS.info) + '</svg>' +
      '<div class="toast__body"><div class="toast__title"></div>' +
      (opts.text ? '<div class="toast__text"></div>' : "") + "</div>" +
      '<button class="btn btn--ghost btn--icon btn--sm" aria-label="Dismiss">' +
      '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" ' +
      'stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg></button>';
    el.querySelector(".toast__title").textContent = opts.title || "Notification";
    if (opts.text) el.querySelector(".toast__text").textContent = opts.text;
    function dismiss() { el.classList.add("is-leaving"); setTimeout(function () { el.remove(); }, 160); }
    el.querySelector("button").addEventListener("click", dismiss);
    stack.appendChild(el);
    if (opts.duration !== 0) setTimeout(dismiss, opts.duration || 4200);
  };
  document.querySelectorAll("[data-toast]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      window.lumoToast({
        type:  btn.getAttribute("data-toast") || "info",
        title: btn.getAttribute("data-toast-title") || "Saved",
        text:  btn.getAttribute("data-toast-text") || ""
      });
    });
  });

  /* ---- Mobile sidebar toggle --------------------------------------------- */
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-nav-toggle]")) {
      document.querySelector(".app") && document.querySelector(".app").classList.toggle("nav-open");
    }
    if (e.target.classList && e.target.classList.contains("scrim")) {
      document.querySelector(".app") && document.querySelector(".app").classList.remove("nav-open");
    }
  });

  /* ---- Demo-only inline validation --------------------------------------- */
  document.querySelectorAll("[data-validate-demo]").forEach(function (input) {
    input.addEventListener("input", function () {
      var field = input.closest(".field");
      field.classList.remove("is-error", "is-success");
      if (input.value.trim() === "") return;
      field.classList.add(input.value.trim().length >= 3 ? "is-success" : "is-error");
    });
  });
})();
