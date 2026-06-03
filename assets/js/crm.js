/* =========================================================================
   Verum Advisory — CRM (Engagement Register)
   Client-side only. Persists to localStorage. No backend, no data leaves
   this browser. Works from file:// as well as http(s)://.
   ========================================================================= */
(function () {
  "use strict";

  var KEY = "verum.crm.v1";
  var STAGES = ["Prospect", "Conversation", "Engaged", "Active", "Dormant"];
  var AREAS = ["Cross-Border", "Transactions", "Controversy", "Private Capital"];

  var money = new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD", maximumFractionDigits: 0
  });

  var SEED = [
    { id: uid(), name: "Halsted Maritime Group", org: "Holding — Luxembourg", email: "office@halsted.example", phone: "", juris: "LU / US", area: "Cross-Border", stage: "Active", value: 480000, notes: "Treaty position memorialized Q1. No open items." },
    { id: uid(), name: "Arden Family Office", org: "Private capital", email: "trustee@arden.example", phone: "", juris: "US / CH", area: "Private Capital", stage: "Engaged", value: 320000, notes: "Succession structure in draft. Founder review pending." },
    { id: uid(), name: "Northwind Acquisitions", org: "PE — carve-out", email: "deals@northwind.example", phone: "", juris: "US / IE", area: "Transactions", stage: "Conversation", value: 0, notes: "Modeling tax before term sheet. Call Thursday." },
    { id: uid(), name: "Calder Industrial", org: "Manufacturing group", email: "cfo@calder.example", phone: "", juris: "US / MX", area: "Controversy", stage: "Active", value: 210000, notes: "Federal examination. Documentation assembled and filed." },
    { id: uid(), name: "Meridian Holdings", org: "Real assets", email: "ir@meridian.example", phone: "", juris: "US", area: "Cross-Border", stage: "Prospect", value: 0, notes: "Introduction via Arden. Awaiting first conversation." }
  ];

  // ---- storage ---------------------------------------------------------
  function uid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "id-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
  }
  function load() {
    try {
      var raw = JSON.parse(localStorage.getItem(KEY));
      return Array.isArray(raw) ? raw : null;
    } catch (e) { return null; }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }

  var state = load();
  if (!state) { state = SEED.slice(); save(); }

  // ---- elements --------------------------------------------------------
  var els = {
    stats:   document.getElementById("crm-stats"),
    body:    document.getElementById("crm-body"),
    search:  document.getElementById("crm-search"),
    fStage:  document.getElementById("crm-filter-stage"),
    fArea:   document.getElementById("crm-filter-area"),
    form:    document.getElementById("crm-form"),
    formTitle: document.getElementById("crm-form-title"),
    submit:  document.getElementById("crm-submit"),
    cancel:  document.getElementById("crm-cancel"),
    reset:   document.getElementById("crm-reset"),
    exportBtn: document.getElementById("crm-export"),
    // fields
    fid: document.getElementById("f-id"),
    fname: document.getElementById("f-name"),
    forg: document.getElementById("f-org"),
    femail: document.getElementById("f-email"),
    fphone: document.getElementById("f-phone"),
    fjuris: document.getElementById("f-juris"),
    farea: document.getElementById("f-area"),
    fstage: document.getElementById("f-stage"),
    fvalue: document.getElementById("f-value"),
    fnotes: document.getElementById("f-notes")
  };
  if (!els.body) return; // not on CRM page

  // populate selects
  fill(els.farea, AREAS);
  fill(els.fstage, STAGES);
  fill(els.fArea, AREAS, "All practices");
  fill(els.fStage, STAGES, "All stages");

  function fill(sel, items, allLabel) {
    if (!sel) return;
    var html = allLabel ? '<option value="">' + allLabel + "</option>" : "";
    items.forEach(function (i) { html += '<option value="' + i + '">' + i + "</option>"; });
    sel.innerHTML = html;
  }

  // ---- render ----------------------------------------------------------
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function visible() {
    var q = (els.search.value || "").trim().toLowerCase();
    var fs = els.fStage.value, fa = els.fArea.value;
    return state.filter(function (c) {
      if (fs && c.stage !== fs) return false;
      if (fa && c.area !== fa) return false;
      if (q) {
        var hay = (c.name + " " + c.org + " " + c.juris + " " + c.notes).toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });
  }

  function renderStats() {
    var total = state.length;
    var active = state.filter(function (c) { return c.stage === "Active"; }).length;
    var pipeline = state.reduce(function (s, c) { return s + (Number(c.value) || 0); }, 0);
    var openConv = state.filter(function (c) {
      return c.stage === "Prospect" || c.stage === "Conversation";
    }).length;

    els.stats.innerHTML =
      stat(total, "Engagements") +
      stat(active, "Active files", true) +
      stat(money.format(pipeline), "Pipeline value") +
      stat(openConv, "In conversation");
  }
  function stat(figure, label, gold) {
    return '<div class="crm-stat"><span class="figure' + (gold ? " is-gold" : "") +
      '">' + escapeHtml(figure) + '</span><span class="label">' + label + "</span></div>";
  }

  function renderTable() {
    var rows = visible();
    if (!rows.length) {
      els.body.innerHTML =
        '<tr><td colspan="6"><div class="crm-empty"><span class="mono">NO MATCHING RECORDS</span>' +
        "Adjust the filters, or add an engagement above.</div></td></tr>";
      return;
    }
    els.body.innerHTML = rows.map(function (c) {
      return "<tr>" +
        '<td><span class="c-name">' + escapeHtml(c.name) + "</span>" +
          (c.org ? '<span class="c-org">' + escapeHtml(c.org) + "</span>" : "") +
          (c.notes ? '<span class="crm-note-line">' + escapeHtml(c.notes) + "</span>" : "") +
        "</td>" +
        '<td class="c-juris">' + escapeHtml(c.juris || "—") + "</td>" +
        "<td>" + escapeHtml(c.area) + "</td>" +
        '<td><span class="stage stage--' + escapeHtml(c.stage) + '">' + escapeHtml(c.stage) + "</span></td>" +
        '<td class="c-value">' + (Number(c.value) ? money.format(c.value) : "—") + "</td>" +
        '<td><div class="crm-actions">' +
          '<button class="crm-link crm-link--gold" data-edit="' + c.id + '">Edit</button>' +
          '<button class="crm-link crm-link--danger" data-del="' + c.id + '">Remove</button>' +
        "</div></td>" +
      "</tr>";
    }).join("");
  }

  function render() { renderStats(); renderTable(); }

  // ---- form ------------------------------------------------------------
  function resetForm() {
    els.form.reset();
    els.fid.value = "";
    els.formTitle.textContent = "Add an engagement";
    els.submit.textContent = "Add engagement";
    els.cancel.hidden = true;
  }

  function startEdit(id) {
    var c = state.find(function (x) { return x.id === id; });
    if (!c) return;
    els.fid.value = c.id;
    els.fname.value = c.name;
    els.forg.value = c.org || "";
    els.femail.value = c.email || "";
    els.fphone.value = c.phone || "";
    els.fjuris.value = c.juris || "";
    els.farea.value = c.area;
    els.fstage.value = c.stage;
    els.fvalue.value = c.value || "";
    els.fnotes.value = c.notes || "";
    els.formTitle.textContent = "Edit engagement";
    els.submit.textContent = "Save changes";
    els.cancel.hidden = false;
    els.form.scrollIntoView({ behavior: "smooth", block: "start" });
    els.fname.focus();
  }

  els.form.addEventListener("submit", function (e) {
    e.preventDefault();
    var name = els.fname.value.trim();
    if (!name) { els.fname.focus(); return; }
    var record = {
      name: name,
      org: els.forg.value.trim(),
      email: els.femail.value.trim(),
      phone: els.fphone.value.trim(),
      juris: els.fjuris.value.trim(),
      area: els.farea.value || AREAS[0],
      stage: els.fstage.value || STAGES[0],
      value: Number(els.fvalue.value) || 0,
      notes: els.fnotes.value.trim()
    };
    var editing = els.fid.value;
    if (editing) {
      var i = state.findIndex(function (x) { return x.id === editing; });
      if (i > -1) state[i] = Object.assign({}, state[i], record);
    } else {
      record.id = uid();
      state.unshift(record);
    }
    save();
    resetForm();
    render();
  });

  els.cancel.addEventListener("click", resetForm);

  // delegated edit / delete
  els.body.addEventListener("click", function (e) {
    var ed = e.target.getAttribute("data-edit");
    var dl = e.target.getAttribute("data-del");
    if (ed) startEdit(ed);
    if (dl) {
      var c = state.find(function (x) { return x.id === dl; });
      if (c && window.confirm("Remove " + c.name + " from the register?")) {
        state = state.filter(function (x) { return x.id !== dl; });
        save();
        render();
      }
    }
  });

  // filters / search
  [els.search, els.fStage, els.fArea].forEach(function (el) {
    el.addEventListener("input", renderTable);
  });

  // reset all data
  els.reset.addEventListener("click", function () {
    if (window.confirm("Restore the example register? This replaces all current records in this browser.")) {
      state = SEED.slice();
      save();
      resetForm();
      render();
    }
  });

  // export CSV
  els.exportBtn.addEventListener("click", function () {
    var head = ["Name", "Organization", "Email", "Phone", "Jurisdiction", "Practice", "Stage", "Value"];
    var lines = [head.join(",")];
    state.forEach(function (c) {
      lines.push([c.name, c.org, c.email, c.phone, c.juris, c.area, c.stage, c.value]
        .map(function (v) { return '"' + String(v == null ? "" : v).replace(/"/g, '""') + '"'; })
        .join(","));
    });
    var blob = new Blob([lines.join("\n")], { type: "text/csv" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "verum-engagements.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  });

  resetForm();
  render();
})();
