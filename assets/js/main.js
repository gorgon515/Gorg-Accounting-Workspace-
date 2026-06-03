/* Verum Advisory — interaction layer. Restrained by design. */
(function () {
  "use strict";

  /* Header hairline on scroll */
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("is-scrolled", window.scrollY > 12);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
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

  /* Client Portal tabs */
  var tabButtons = document.querySelectorAll(".portal-tabbtn");
  if (tabButtons.length) {
    tabButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var target = btn.getAttribute("data-panel");
        tabButtons.forEach(function (b) {
          b.setAttribute("aria-selected", String(b === btn));
        });
        document.querySelectorAll(".portal-panel").forEach(function (panel) {
          panel.classList.toggle("is-active", panel.id === target);
        });
      });
    });
  }

  /* Demo form handling — no backend; acknowledge quietly */
  document.querySelectorAll("form[data-demo]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
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

  /* ---- Generated document downloads — make portal links open real files -- */
  function downloadFile(name, text) {
    var blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }
  function letterhead(title, body) {
    var rule = "────────────────────────────────────────────────";
    return [
      "VERUM ADVISORY",
      "International Tax Advisory",
      rule, "",
      title.toUpperCase(), "",
      body, "",
      rule,
      "Verum Advisory Group, Inc. · One Bryant Park, New York, NY 10036",
      "PRIVILEGED & CONFIDENTIAL — prepared for the named client only.",
      "Reference: VA-" + Math.random().toString(36).slice(2, 8).toUpperCase()
    ].join("\n");
  }
  document.querySelectorAll("[data-file]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      e.preventDefault();
      var name = el.getAttribute("data-file");
      var title = el.getAttribute("data-file-title") || name;
      var body = el.getAttribute("data-file-body") ||
        "This is a demonstration document generated locally in your browser. " +
        "In production, the executed file would be served from secure storage.";
      downloadFile(name, letterhead(title, body));
      var prev = el.textContent;
      el.textContent = "Downloaded ✓";
      setTimeout(function () { el.textContent = prev; }, 1800);
    });
  });

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
