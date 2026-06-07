/* Renders a single client document into document.html from VERUM_DOCS. */
(function () {
  "use strict";
  var data = window.VERUM_DOCS || { order: [], items: {} };
  var id = new URLSearchParams(location.search).get("id");
  if (!id || !data.items[id]) id = data.order[0];
  var d = data.items[id];

  function set(sel, text) { var el = document.querySelector(sel); if (el) el.textContent = text; }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  if (!d) { set("#d-title", "Document not found"); return; }

  document.title = d.title + " — Verum Advisory";
  set("#d-kind", d.kind);
  set("#d-ref", d.ref);
  set("#d-date", d.date);
  set("#d-title", d.title);

  var html = "";
  (d.body || []).forEach(function (p) {
    html += d.pre ? '<pre class="doc-pre">' + esc(p) + "</pre>" : "<p>" + esc(p) + "</p>";
  });
  if (d.lines) {
    html += '<div class="doc-ledger">';
    d.lines.forEach(function (row) {
      html += '<div class="ledger-row"><span>' + esc(row[0]) + '</span><span class="mono">' + esc(row[1]) + "</span></div>";
    });
    html += '<div class="ledger-row ledger-total"><span>Balance due</span><span class="mono">' + esc(d.total || "$0.00") + "</span></div>";
    html += "</div>";
  }
  document.getElementById("d-body").innerHTML = html;

  // Plain-text download, generated on letterhead
  function plain() {
    var rule = "--------------------------------------------------";
    var lines = ["VERUM ADVISORY", "International Tax Advisory", rule, "",
      d.kind.toUpperCase() + "  ·  " + d.ref + "  ·  " + d.date, "",
      d.title.toUpperCase(), ""];
    (d.body || []).forEach(function (p) { lines.push(p, ""); });
    if (d.lines) {
      d.lines.forEach(function (r) { lines.push(r[0] + "   " + r[1]); });
      lines.push("Balance due   " + (d.total || "$0.00"), "");
    }
    lines.push(rule, "Verum Advisory Group, Inc. · One Bryant Park, New York, NY 10036",
      "PRIVILEGED & CONFIDENTIAL — prepared for the named client only.");
    return lines.join("\n");
  }
  var btn = document.getElementById("d-download");
  if (btn) {
    btn.addEventListener("click", function () {
      var blob = new Blob([plain()], { type: "text/plain;charset=utf-8" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "Verum-" + id + ".txt";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
      var t = btn.querySelector("[data-label]");
      if (t) { var was = t.textContent; t.textContent = "Downloaded ✓"; setTimeout(function () { t.textContent = was; }, 1800); }
    });
  }
})();
