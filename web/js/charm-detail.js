// The right pane: full charm details with a clickable prerequisite graph.
import { viewerState } from "./state.js";
import { elementById, escapeHtml } from "./dom-utils.js";
import { renderCharmList } from "./charm-list.js";

// prerequisites and children are lists of { name, charmId }. A charmId that
// points to a known charm renders as a clickable link; a null charmId (or a
// free-text entry like "any 5 Lore Charms") renders as plain text.
function graphEntryHtml(entry) {
  if (entry.charmId && viewerState.charmsById.has(entry.charmId)) {
    return `<span class="link" data-goto="${entry.charmId}">${escapeHtml(entry.name)}</span>`;
  }
  return `<span class="rawreq">${escapeHtml(entry.name)}</span>`;
}

function graphEntriesHtml(entries) {
  if (!entries.length) return `<span class="rawreq">None</span>`;
  return entries.map(graphEntryHtml).join("");
}

export function showCharmDetail(charmId) {
  const charm = viewerState.charmsById.get(charmId);
  if (!charm) return;
  viewerState.openCharmId = charmId;
  renderCharmList(); // refresh the active-row highlight
  history.replaceState(null, "", "#" + charm.id); // deep-linkable URL

  // Merits use a different stat block (rating + type, no cost/keywords/tree).
  const isMerit = charm.category.endsWith(" Merits");
  const statRows = isMerit
    ? [["Rating", charm.rating], ["Type", charm.type]]
    : [["Cost", charm.cost], ["Mins", charm.mins],
       ["Type", charm.type], ["Duration", charm.duration]];
  const statRowsHtml = statRows
    .filter(([, value]) => value)
    .map(([label, value]) => `<dt>${label}</dt><dd>${escapeHtml(value)}</dd>`)
    .join("");

  const keywordsHtml = charm.keywords.length
    ? charm.keywords.map(
        (keyword) => `<span class="kw">${escapeHtml(keyword)}</span>`).join("")
    : `<span class="rawreq">None</span>`;
  const keywordsRowHtml = isMerit
    ? "" : `<dt>Keywords</dt><dd>${keywordsHtml}</dd>`;

  const treeHtml = isMerit ? "" :
    `<div class="tree"><h3>Prerequisites</h3><div>${graphEntriesHtml(charm.prerequisites)}</div></div>
     <div class="tree"><h3>Leads to</h3><div>${graphEntriesHtml(charm.children)}</div></div>`;

  const descriptionHtml = charm.description.split("\n\n")
    .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("");

  const detailPane = elementById("charmDetail");
  detailPane.innerHTML = `
    <h2>${escapeHtml(charm.name)}</h2>
    <div class="cat-line">${escapeHtml(charm.category)} · page ${charm.page}</div>
    <dl class="stats">
      ${statRowsHtml}
      ${keywordsRowHtml}
    </dl>
    ${treeHtml}
    <div class="desc">${descriptionHtml}</div>
  `;
  detailPane.querySelectorAll(".link[data-goto]").forEach((linkElement) => {
    linkElement.onclick = () => showCharmDetail(linkElement.dataset.goto);
  });
  detailPane.scrollTop = 0;
}
