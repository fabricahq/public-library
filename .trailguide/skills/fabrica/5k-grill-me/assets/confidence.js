function confidenceInfoIcon() {
  return `<svg class="confidence-info-icon" viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="3" width="14" height="14" rx="4"/><path d="M10 9.2v4.2"/><circle cx="10" cy="6.8" r=".85" class="info-dot"/></svg>`;
}
const confidenceHelpCopy = {
  context: {
    title: "Context confidence",
    text: "How sure the agent is that the session context establishes your intended decision.",
    high: "Clearly stated and consistent.",
    low: "Missing, ambiguous, or conflicting.",
  },
  recommendation: {
    title: "Recommendation confidence",
    text: "How sure the agent is that its proposed direction is a good choice.",
    high: "Strong reasons to prefer it.",
    low: "Unresolved tradeoffs or missing information.",
  },
};
function confidenceHelp(kind) {
  return `<button type="button" class="confidence-help" data-confidence-help="${kind}" aria-label="About ${confidenceHelpCopy[kind].title.toLowerCase()}">${confidenceInfoIcon()}</button>`;
}
const helpTooltip = document.createElement("div");
helpTooltip.id = "confidenceHelpTooltip";
helpTooltip.className = "confidence-tooltip";
helpTooltip.role = "tooltip";
helpTooltip.hidden = true;
document.body.append(helpTooltip);
let activeHelp = null,
  helpPinned = false,
  helpHideTimer;
function hideConfidenceHelp() {
  clearTimeout(helpHideTimer);
  activeHelp?.removeAttribute("aria-describedby");
  activeHelp = null;
  helpPinned = false;
  helpTooltip.hidden = true;
}
function showConfidenceHelp(button) {
  clearTimeout(helpHideTimer);
  if (activeHelp !== button) {
    activeHelp?.removeAttribute("aria-describedby");
    helpPinned = false;
  }
  activeHelp = button;
  const copy = confidenceHelpCopy[button.dataset.confidenceHelp];
  helpTooltip.innerHTML = `<strong>${copy.title}</strong><p>${copy.text}</p><dl class="confidence-examples"><div><dt class="example-high">High</dt><dd>${copy.high}</dd></div><div><dt class="example-low">Low</dt><dd>${copy.low}</dd></div></dl>`;
  helpTooltip.hidden = false;
  button.setAttribute("aria-describedby", helpTooltip.id);
  const anchor = button.getBoundingClientRect(),
    tip = helpTooltip.getBoundingClientRect();
  const left = Math.max(
    12,
    Math.min(
      innerWidth - tip.width - 12,
      anchor.left + anchor.width / 2 - tip.width / 2,
    ),
  );
  const below = anchor.bottom + 9;
  const top =
    below + tip.height <= innerHeight - 12
      ? below
      : Math.max(12, anchor.top - tip.height - 9);
  helpTooltip.style.left = left + "px";
  helpTooltip.style.top = top + "px";
}
function deferConfidenceHelpHide() {
  clearTimeout(helpHideTimer);
  helpHideTimer = setTimeout(() => {
    if (
      !helpPinned &&
      document.activeElement !== activeHelp &&
      !helpTooltip.matches(":hover")
    )
      hideConfidenceHelp();
  }, 130);
}
document.addEventListener("pointerover", (event) => {
  const button = event.target.closest(".confidence-help");
  if (button) showConfidenceHelp(button);
  else if (helpTooltip.contains(event.target)) clearTimeout(helpHideTimer);
});
document.addEventListener("pointerout", (event) => {
  const button = event.target.closest(".confidence-help");
  if (button && !button.contains(event.relatedTarget))
    deferConfidenceHelpHide();
  else if (
    helpTooltip.contains(event.target) &&
    !helpTooltip.contains(event.relatedTarget)
  )
    deferConfidenceHelpHide();
});
document.addEventListener("focusin", (event) => {
  if (event.target.matches(".confidence-help"))
    showConfidenceHelp(event.target);
});
document.addEventListener("focusout", (event) => {
  if (event.target.matches(".confidence-help")) deferConfidenceHelpHide();
});
document.addEventListener(
  "click",
  (event) => {
    const button = event.target.closest(".confidence-help");
    if (button) {
      event.preventDefault();
      event.stopPropagation();
      if (activeHelp === button && helpPinned) hideConfidenceHelp();
      else {
        showConfidenceHelp(button);
        helpPinned = true;
      }
    } else if (!helpTooltip.contains(event.target)) hideConfidenceHelp();
  },
  true,
);
document.addEventListener(
  "keydown",
  (event) => {
    if (event.key === "Escape" && activeHelp) {
      event.preventDefault();
      event.stopPropagation();
      hideConfidenceHelp();
    }
  },
  true,
);
document.addEventListener("scroll", hideConfidenceHelp, true);
window.addEventListener("resize", hideConfidenceHelp);
document.addEventListener("change", hideConfidenceHelp);

const clarificationLabels = [
  "Most to clarify",
  "More to clarify",
  "Some to clarify",
  "Less to clarify",
  "Least to clarify",
];
const assessedLevels = ["Low", "Medium", "High"];
const allConfidencePairs = assessedLevels.flatMap((context) =>
  assessedLevels.map((advice) => `${context},${advice}`),
);
let selectedConfidencePairs = new Set(allConfidencePairs);
let includeUnassessed = true;
function setConfidencePair(context, advice) {
  selectedConfidencePairs = new Set([`${context},${advice}`]);
  includeUnassessed = false;
  applyConfidenceFilters();
}
function isConfidencePairFocused(context, advice) {
  return (
    !includeUnassessed &&
    selectedConfidencePairs.size === 1 &&
    selectedConfidencePairs.has(`${context},${advice}`)
  );
}

const confidenceGroupMenu = document.createElement("div");
confidenceGroupMenu.id = "confidenceGroupMenu";
confidenceGroupMenu.className = "confidence-group-menu";
confidenceGroupMenu.setAttribute("role", "dialog");
confidenceGroupMenu.setAttribute("aria-labelledby", "confidenceGroupHeading");
confidenceGroupMenu.hidden = true;
document.body.append(confidenceGroupMenu);
function resetConfidenceGroups() {
  selectedConfidencePairs = new Set(allConfidencePairs);
  includeUnassessed = true;
}
function renderConfidenceGroupControls() {
  const active = confidenceFiltered();
  const trigger = $("confidenceGroups");
  trigger.classList.toggle("is-filtered", active);
  trigger.innerHTML = `<svg class="filter-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 4h14l-5.5 6.5V16l-3-1.5v-4z"/></svg><span>Filter questions</span>${active ? '<span class="filter-active">On</span>' : ""}<svg class="select-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg>`;
  trigger.setAttribute(
    "aria-label",
    `Filter questions${active ? ": active" : ""}`,
  );
  confidenceGroupMenu.querySelectorAll("[data-pair]").forEach((button) => {
    button.setAttribute(
      "aria-checked",
      String(selectedConfidencePairs.has(button.dataset.pair)),
    );
  });
  $("includeUnassessed").checked = includeUnassessed;
}
function closeConfidenceGroupMenu(restoreFocus = false) {
  if (confidenceGroupMenu.hidden) return;
  confidenceGroupMenu.hidden = true;
  $("confidenceGroups").setAttribute("aria-expanded", "false");
  if (restoreFocus) $("confidenceGroups").focus();
}
function openConfidenceGroupMenu() {
  if (!confidenceGroupMenu.hidden) {
    closeConfidenceGroupMenu();
    return;
  }
  hideConfidenceHelp();
  renderConfidenceGroupControls();
  confidenceGroupMenu.hidden = false;
  $("confidenceGroups").setAttribute("aria-expanded", "true");
  const anchor = $("confidenceGroups").getBoundingClientRect();
  const menu = confidenceGroupMenu.getBoundingClientRect();
  confidenceGroupMenu.style.left =
    Math.max(12, Math.min(innerWidth - menu.width - 12, anchor.left)) + "px";
  confidenceGroupMenu.style.top =
    Math.max(12, Math.min(innerHeight - menu.height - 12, anchor.bottom + 8)) +
    "px";
  confidenceGroupMenu.querySelector("[data-pair]").focus();
}
function initConfidenceGroupControls() {
  const check = '<span class="group-check" aria-hidden="true">✓</span>';
  let grid = `<div class="group-y-label"><span>Recommendation confidence</span>${confidenceHelp("recommendation")}</div>`;
  grid += assessedLevels
    .map(
      (level, column) =>
        `<span class="group-axis" style="grid-column:${column + 3};grid-row:2">${level}</span>`,
    )
    .join("");
  for (const [row, advice] of [...assessedLevels].reverse().entries()) {
    grid += `<span class="group-axis group-row-label" style="grid-column:2;grid-row:${row + 3}">${advice}</span>`;
    for (const [column, context] of assessedLevels.entries()) {
      const score =
        assessedLevels.indexOf(context) + assessedLevels.indexOf(advice);
      grid += `<button class="group-cell certainty-${score}" style="grid-column:${column + 3};grid-row:${row + 3}" role="checkbox" aria-checked="true" data-pair="${context},${advice}" aria-label="${context} context, ${advice} recommendation: ${clarificationLabels[score]}">${check}<span class="group-clarification">${clarificationLabels[score]}</span></button>`;
    }
  }
  confidenceGroupMenu.innerHTML = `<div class="group-heading"><h3 id="confidenceGroupHeading">Show questions</h3><button id="closeConfidenceGroups" aria-label="Close question filter">×</button></div><div class="group-grid"><div class="group-x-label">Context confidence ${confidenceHelp("context")}</div>${grid}</div><label class="group-unassessed"><input type="checkbox" id="includeUnassessed" checked><span>Include unassessed</span></label><div class="group-footer"><div class="group-actions"><button id="allConfidenceGroups" aria-label="Show all questions">All</button><button id="noConfidenceGroups" aria-label="Hide all questions">None</button></div><button id="finishConfidenceGroups">Done</button></div>`;
  confidenceGroupMenu.querySelectorAll("[data-pair]").forEach((button) => {
    button.onclick = () => {
      const pair = button.dataset.pair;
      if (selectedConfidencePairs.has(pair))
        selectedConfidencePairs.delete(pair);
      else selectedConfidencePairs.add(pair);
      applyConfidenceFilters();
    };
  });
  $("includeUnassessed").onchange = (event) => {
    includeUnassessed = event.target.checked;
    applyConfidenceFilters();
  };
  $("allConfidenceGroups").onclick = () => {
    resetConfidenceGroups();
    applyConfidenceFilters();
  };
  $("noConfidenceGroups").onclick = () => {
    selectedConfidencePairs.clear();
    includeUnassessed = false;
    applyConfidenceFilters();
  };
  $("closeConfidenceGroups").onclick = () => closeConfidenceGroupMenu(true);
  $("finishConfidenceGroups").onclick = () => closeConfidenceGroupMenu(true);
  $("confidenceGroups").onclick = openConfidenceGroupMenu;
  $("confidenceGroups").onkeydown = (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (confidenceGroupMenu.hidden) openConfidenceGroupMenu();
    }
  };
  document.addEventListener("click", (event) => {
    if (
      !confidenceGroupMenu.contains(event.target) &&
      !event.composedPath().includes($("confidenceGroups"))
    )
      closeConfidenceGroupMenu();
  });
  document.addEventListener("focusin", (event) => {
    if (
      !confidenceGroupMenu.contains(event.target) &&
      !event.composedPath().includes($("confidenceGroups"))
    )
      closeConfidenceGroupMenu();
  });
  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key === "Escape" && !confidenceGroupMenu.hidden) {
        event.preventDefault();
        event.stopImmediatePropagation();
        closeConfidenceGroupMenu(true);
      }
    },
    true,
  );
  window.addEventListener("resize", () => closeConfidenceGroupMenu());
  document.addEventListener(
    "scroll",
    (event) => {
      if (!confidenceGroupMenu.contains(event.target))
        closeConfidenceGroupMenu();
    },
    true,
  );
}

let confidenceMode = "tree";
function confidenceAssessment(node, kind) {
  if (
    kind === "recommendation" &&
    !(
      node.agentRecommendationSummary?.trim() ||
      node.agentRecommendation?.trim()
    )
  )
    return null;
  return node[kind + "Confidence"] || null;
}
function confidenceLevel(node, kind) {
  const assessment = confidenceAssessment(node, kind);
  return assessment
    ? assessment.level[0].toUpperCase() + assessment.level.slice(1)
    : "Not assessed";
}
function confidencePairMatches(context, advice) {
  const assessed = context !== "Not assessed" && advice !== "Not assessed";
  return assessed
    ? selectedConfidencePairs.has(`${context},${advice}`)
    : includeUnassessed;
}
function confidenceMatches(node) {
  return confidencePairMatches(
    confidenceLevel(node, "context"),
    confidenceLevel(node, "recommendation"),
  );
}
function confidenceHits() {
  return session.nodes.filter(confidenceMatches);
}
function confidenceFiltered() {
  return (
    selectedConfidencePairs.size !== allConfidencePairs.length ||
    !includeUnassessed
  );
}
function clearConfidenceFilters() {
  resetConfidenceGroups();
  applyConfidenceFilters();
}
function confidenceOutsideNotice(node) {
  return confidenceMatches(node)
    ? ""
    : '<p class="confidence-outside">Outside the current filter. Kept open while you explore.</p>';
}
function confidenceDetails(node) {
  return (
    '<section class="confidence-detail" aria-label="Confidence assessment">' +
    ["context", "recommendation"]
      .map((kind) => {
        const assessment = confidenceAssessment(node, kind),
          level = confidenceLevel(node, kind);
        return `<details><summary>${confidenceHelpCopy[kind].title}${confidenceHelp(kind)}<span class="confidence-level confidence-${assessment ? assessment.level : "unrated"}">${level}</span></summary><p>${esc(assessment?.reason || "The agent has not assessed this confidence level yet.")}</p>${assessment?.evidence ? `<blockquote><strong>Supporting context</strong>${esc(assessment.evidence)}</blockquote>` : ""}</details>`;
      })
      .join("") +
    "</section>"
  );
}
function matrixQuestion(node) {
  return `<button class="matrix-decision" data-confidence-node="${esc(node.id)}" aria-label="${esc(node.id + " " + node.title)}" aria-pressed="${selected === node.id}" title="${esc(node.title)}"><span class="matrix-id">${esc(node.id)}</span><span class="matrix-title">${esc(node.title)}</span><span class="matrix-status">${newQuestionMark(node)}${statusMark(node)}</span></button>`;
}
function updateOverflowHints() {
  const lists = [
    ...$("confidenceMatrix").querySelectorAll(".confidence-cell-list"),
  ];
  lists.forEach((list) => {
    list.style.maxHeight = "";
  });
  // A complete row is easier to scan than fragments at both edges of each cell.
  const heights = lists.map((list) =>
    list.querySelector(".matrix-decision")
      ? Math.max(1, Math.floor((list.clientHeight + 1) / 41)) * 41 - 1
      : null,
  );
  lists.forEach((list, index) => {
    if (heights[index] !== null) list.style.maxHeight = heights[index] + "px";
    list.parentElement.classList.toggle(
      "list-overflow",
      list.scrollHeight > list.clientHeight + 2,
    );
  });
}
window.addEventListener("resize", updateOverflowHints);

function renderConfidenceMatrix() {
  const levels = ["Low", "Medium", "High"];
  const scroll = new Map(
    [...$("confidenceMatrix").querySelectorAll(".confidence-cell")].map(
      (cell) => [
        cell.getAttribute("aria-label"),
        cell.querySelector(".confidence-cell-list").scrollTop,
      ],
    ),
  );
  let markup = `<div class="matrix-overview"><p>${confidenceFiltered() ? "Showing your selected confidence groups." : "Start where both confidence levels are low."} <button id="jumpUncertain">${confidenceFiltered() ? "Switch to" : "Explore"} Low / Low →</button></p><div class="uncertainty-key"><span>More to clarify</span><i class="key-warm"></i><i class="key-mid"></i><i class="key-cool"></i><span>Less to clarify</span></div></div><p class="matrix-pan-hint">Swipe sideways to see all confidence columns.</p><div class="matrix-x-axis"><span>Context confidence →</span>${confidenceHelp("context")}</div><div class="confidence-grid"><div class="matrix-y-axis"><span>Recommendation confidence →</span>${confidenceHelp("recommendation")}</div>`;
  markup += levels
    .map(
      (x, i) =>
        `<div class="matrix-column-title" style="grid-column:${i + 3};grid-row:1">${x}</div>`,
    )
    .join("");
  for (const [row, advice] of ["High", "Medium", "Low"].entries()) {
    markup += `<div class="matrix-row-title" style="grid-column:2;grid-row:${row + 2}">${advice}</div>`;
    for (const [column, context] of levels.entries()) {
      const allMembers = session.nodes.filter(
        (n) =>
          confidenceLevel(n, "context") === context &&
          confidenceLevel(n, "recommendation") === advice,
      );
      const included = confidencePairMatches(context, advice);
      if (!included) {
        markup += `<section class="confidence-cell excluded" style="grid-column:${column + 3};grid-row:${row + 2}" aria-label="${context} context confidence, ${advice} recommendation confidence"><div class="confidence-cell-list"><p class="matrix-nothing">Filtered out</p></div></section>`;
        continue;
      }
      const active = isConfidencePairFocused(context, advice);
      const certainty = levels.indexOf(context) + levels.indexOf(advice);
      const label = clarificationLabels[certainty];
      markup += `<section class="confidence-cell certainty-${certainty} ${active ? "is-focused" : ""}" style="grid-column:${column + 3};grid-row:${row + 2}" aria-label="${context} context confidence, ${advice} recommendation confidence"><div class="confidence-cell-top"><strong>${label}</strong><button data-confidence-cell="${context},${advice}" aria-label="${active ? "Clear focus" : "Focus on " + context.toLowerCase() + " context and " + advice.toLowerCase() + " recommendation confidence"}" ${!allMembers.length && !active ? "disabled" : ""}>${active ? "Clear focus ×" : "Focus"}</button></div><div class="cell-count">${allMembers.length} ${allMembers.length === 1 ? "question" : "questions"}</div><div class="confidence-cell-list">${allMembers.length ? allMembers.map(matrixQuestion).join("") : `<p class="matrix-nothing">No questions in this group</p>`}</div></section>`;
    }
  }
  const unassessed = confidenceHits().filter((n) =>
    ["context", "recommendation"].some(
      (kind) => confidenceLevel(n, kind) === "Not assessed",
    ),
  );
  const extra = unassessed.length
    ? `<section class="confidence-unassessed"><h3>Not assessed · ${unassessed.length} ${unassessed.length === 1 ? "question" : "questions"}</h3><p>These questions need one or both confidence assessments. They are kept outside the matrix rather than assigned a rating.</p><div class="unassessed-list">${unassessed.map(matrixQuestion).join("")}</div></section>`
    : "";
  $("confidenceMatrix").innerHTML = markup + "</div>" + extra;
  $("confidenceMatrix")
    .querySelectorAll(".confidence-cell")
    .forEach((cell) => {
      cell.querySelector(".confidence-cell-list").scrollTop =
        scroll.get(cell.getAttribute("aria-label")) || 0;
    });
  $("jumpUncertain").disabled = !session.nodes.some(
    (n) =>
      confidenceLevel(n, "context") === "Low" &&
      confidenceLevel(n, "recommendation") === "Low",
  );
  if (!includeUnassessed && selectedConfidencePairs.size === 1) {
    const advice = [...selectedConfidencePairs][0].split(",")[1];
    $("confidenceMatrix")
      .querySelector(".confidence-grid")
      .classList.add("focus-" + advice.toLowerCase());
  }
  $("confidenceMatrix")
    .querySelectorAll(".confidence-cell:not(.excluded) .confidence-cell-list")
    .forEach((list) => {
      const hint = document.createElement("span");
      hint.className = "cell-scroll-hint";
      hint.textContent = "Scroll to see all questions ↕";
      list.after(hint);
    });
  requestAnimationFrame(updateOverflowHints);
  $("jumpUncertain").onclick = () => {
    setConfidencePair("Low", "Low");
    requestAnimationFrame(() => {
      $("confidenceMatrix")
        .querySelector(".is-focused")
        .scrollIntoView({ block: "nearest", inline: "nearest" });
    });
  };
  $("confidenceMatrix")
    .querySelectorAll("[data-confidence-node]")
    .forEach((b) => (b.onclick = () => select(b.dataset.confidenceNode)));
  $("confidenceMatrix")
    .querySelectorAll("[data-confidence-cell]")
    .forEach(
      (b) =>
        (b.onclick = () => {
          const [c, a] = b.dataset.confidenceCell.split(",");
          if (isConfidencePairFocused(c, a)) {
            clearConfidenceFilters();
            return;
          }
          setConfidencePair(c, a);
        }),
    );
}

function renderConfidenceView() {
  renderConfidenceGroupControls();
  const hits = confidenceHits();
  $("confidenceCount").innerHTML =
    `<strong>${hits.length}</strong><span>of ${session.nodes.length} questions</span>`;
  $("resetConfidence").disabled = !confidenceFiltered();
  $("confidenceFilterHint").textContent = confidenceFiltered()
    ? hits.length
      ? "Questions outside the filters are dimmed."
      : "No matching questions. Broaden or reset the filters."
    : "";
  $("tree")
    .querySelectorAll("[data-node]")
    .forEach((button) => {
      const node = get(button.dataset.node);
      button
        .closest("foreignObject")
        .classList.toggle("confidence-muted", !confidenceMatches(node));
    });
  if (confidenceFiltered())
    $("nextQuestion").textContent = hits.length
      ? `${hits.length} matching questions →`
      : "No matching questions";
  $("nextQuestion").disabled = hits.length === 0;
  if (confidenceMode === "matrix") renderConfidenceMatrix();
}
function applyConfidenceFilters() {
  hideConfidenceHelp();
  draw();
  // Filter changes do not rebuild the editor or disturb a draft/focus.
  const panel = $("panel"),
    note = panel.querySelector(".confidence-outside");
  if (selected && !confidenceMatches(get(selected))) {
    if (!note)
      panel
        .querySelector(".question-details")
        ?.insertAdjacentHTML(
          "afterend",
          confidenceOutsideNotice(get(selected)),
        );
  } else note?.remove();
  if (selected) {
    panel.querySelector(".question-next")?.remove();
    const node = get(selected);
    if (!node.answer || answerMode(node) === "saved")
      panel.insertAdjacentHTML("beforeend", questionNavigation());
    if ($("panelNextQuestion"))
      $("panelNextQuestion").onclick = () => {
        const next = nextRemainingQuestion();
        if (next) {
          select(next.id);
          revealQuestion(next.id);
        }
      };
  }
}
function revealMatrixQuestion(id) {
  const button = [
    ...$("confidenceMatrix").querySelectorAll("[data-confidence-node]"),
  ].find((button) => button.dataset.confidenceNode === id);
  button?.scrollIntoView({ block: "nearest", inline: "nearest" });
}
function setConfidenceMode(mode) {
  closeConfidenceGroupMenu();
  hideConfidenceHelp();
  confidenceMode = mode;
  const matrix = mode === "matrix";
  $("viewHeading").textContent = matrix ? "Confidence matrix" : "Question tree";
  $("viewHint").textContent = matrix
    ? "Find what needs clarification"
    : "Explore how decisions connect";
  $("canvas").setAttribute("aria-hidden", String(matrix));
  $("canvas").toggleAttribute("inert", matrix);
  $("confidenceMatrix").hidden = !matrix;
  document.body.classList.toggle("confidence-matrix", matrix);
  $("treeView").setAttribute("aria-pressed", String(!matrix));
  $("matrixView").setAttribute("aria-pressed", String(matrix));
  // Documents retain their own layer; switching views never moves the camera.
  renderConfidenceView();
}
function initConfidence() {
  $("openAbout").querySelector("svg").outerHTML = confidenceInfoIcon();
  initConfidenceGroupControls();
  $("resetConfidence").onclick = clearConfidenceFilters;
  $("treeView").onclick = () => setConfidenceMode("tree");
  $("matrixView").onclick = () => setConfidenceMode("matrix");
}
