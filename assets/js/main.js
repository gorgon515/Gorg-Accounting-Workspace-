/* Verum Advisory — interaction layer. Restrained by design. */
(function () {
  "use strict";

  /* Header hairline + scroll progress (rAF-throttled, single listener) */
  var header = document.querySelector(".site-header");
  var progress = document.getElementById("scroll-progress");
  var ticking = false;
  function paintScroll() {
    ticking = false;
    if (header) header.classList.toggle("is-scrolled", window.scrollY > 12);
    if (progress) {
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      var ratio = max > 0 ? Math.min(window.scrollY / max, 1) : 0;
      progress.style.transform = "scaleX(" + ratio + ")";
    }
  }
  if (header || progress) {
    paintScroll();
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(paintScroll); }
    }, { passive: true });
  }

  /* Mobile navigation */
  var toggle = document.querySelector(".nav-toggle");
  var tabs = document.querySelector(".tabs");
  if (toggle && tabs) {
    toggle.addEventListener("click", function () {
      var open = tabs.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
      document.body.style.overflow = open ? "hidden" : "";
    });
    tabs.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        tabs.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        document.body.style.overflow = "";
      }
    });
  }

  /* Reveal on scroll — fade + subtle translate only */
  var revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && revealEls.length) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("is-visible"); });
  }

  /* Client Portal tabs — click + full keyboard support (WAI-ARIA tabs) */
  var tabButtons = Array.prototype.slice.call(document.querySelectorAll(".portal-tabbtn"));
  if (tabButtons.length) {
    var selectTab = function (btn, focus) {
      var target = btn.getAttribute("data-panel");
      tabButtons.forEach(function (b) {
        var on = b === btn;
        b.setAttribute("aria-selected", String(on));
        b.tabIndex = on ? 0 : -1;          // roving tabindex
      });
      document.querySelectorAll(".portal-panel").forEach(function (panel) {
        panel.classList.toggle("is-active", panel.id === target);
      });
      if (focus) btn.focus();
    };
    tabButtons.forEach(function (btn, i) {
      btn.tabIndex = btn.getAttribute("aria-selected") === "true" ? 0 : -1;
      btn.addEventListener("click", function () { selectTab(btn); });
      btn.addEventListener("keydown", function (e) {
        var n = tabButtons.length, next = null;
        if (e.key === "ArrowDown" || e.key === "ArrowRight") next = (i + 1) % n;
        else if (e.key === "ArrowUp" || e.key === "ArrowLeft") next = (i - 1 + n) % n;
        else if (e.key === "Home") next = 0;
        else if (e.key === "End") next = n - 1;
        if (next !== null) { e.preventDefault(); selectTab(tabButtons[next], true); }
      });
    });
  }

  /* Demo form handling — no backend; acknowledge quietly */
  document.querySelectorAll("form[data-demo]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      // Honeypot: if a bot filled the hidden field, silently drop.
      var hp = form.querySelector('input[name="company_website"]');
      if (hp && hp.value) { form.reset(); return; }
      var note = form.querySelector("[data-form-note]");
      if (note) {
        note.textContent = form.getAttribute("data-success") ||
          "Received. A partner will respond within one business day.";
        note.style.color = "var(--gold)";
      }
      form.reset();
    });
  });

  /* ---- Nav preview: "precursor highlight" showing what each tab opens --- */
  var preview = document.getElementById("nav-preview");
  var navLinks = document.querySelectorAll(".tabs a[data-preview]");
  if (preview && navLinks.length) {
    var npKey = preview.querySelector(".np-key");
    var npDesc = preview.querySelector(".np-desc");
    var npList = document.querySelector(".tabs");
    var hide = function () { preview.classList.remove("is-open"); };
    navLinks.forEach(function (a) {
      var show = function () {
        npKey.textContent = a.getAttribute("data-key") || a.textContent.trim();
        npDesc.textContent = a.getAttribute("data-preview");
        preview.classList.add("is-open");
      };
      a.addEventListener("mouseenter", show);
      a.addEventListener("focus", show);
    });
    if (npList) npList.addEventListener("mouseleave", hide);
    preview.addEventListener("mouseleave", hide);
    document.querySelector(".site-header").addEventListener("mouseleave", hide);
  }

  /* ---- Flash an anchored section when navigated to (practice deep links) - */
  function flashHash() {
    if (!location.hash) return;
    var t = document.getElementById(location.hash.slice(1));
    if (t && t.classList.contains("disc")) {
      t.classList.remove("is-flash");
      void t.offsetWidth;
      t.classList.add("is-flash");
    }
  }
  window.addEventListener("hashchange", flashHash);
  flashHash();

  /* Current year */
  var yr = document.querySelector("[data-year]");
  if (yr) yr.textContent = new Date().getFullYear();
})();
