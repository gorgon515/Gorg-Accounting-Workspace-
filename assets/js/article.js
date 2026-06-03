/* Renders a single insight into article.html from VERUM_ARTICLES. */
(function () {
  "use strict";
  var data = window.VERUM_ARTICLES || { order: [], items: {} };
  var params = new URLSearchParams(location.search);
  var id = params.get("id");
  if (!id || !data.items[id]) { id = data.order[0]; }
  var a = data.items[id];

  function set(sel, text) { var el = document.querySelector(sel); if (el) el.textContent = text; }

  if (!a) {
    set("#a-title", "Insight not found");
    return;
  }

  document.title = a.title + " — Verum Advisory";
  set("#a-cat", a.cat);
  set("#a-date", a.date);
  set("#a-title", a.title);
  set("#a-standfirst", a.standfirst);
  document.getElementById("a-body").innerHTML = a.body.join("\n");

  // prev / next within order
  var i = data.order.indexOf(id);
  var prev = i > 0 ? data.order[i - 1] : null;
  var next = i < data.order.length - 1 ? data.order[i + 1] : null;
  var prevEl = document.getElementById("a-prev");
  var nextEl = document.getElementById("a-next");
  if (prev) { prevEl.href = "article.html?id=" + prev; prevEl.textContent = "← " + data.items[prev].title; }
  else { prevEl.style.visibility = "hidden"; }
  if (next) { nextEl.href = "article.html?id=" + next; nextEl.textContent = data.items[next].title + " →"; }
  else { nextEl.style.visibility = "hidden"; }
})();
