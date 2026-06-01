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

  /* Current year */
  var yr = document.querySelector("[data-year]");
  if (yr) yr.textContent = new Date().getFullYear();
})();
