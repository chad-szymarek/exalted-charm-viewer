// The middle column: filtered charm list with search and selection checkboxes.
import { viewerState } from "./state.js";
import { elementById, escapeHtml } from "./dom-utils.js";
import { showCharmDetail } from "./charm-detail.js";
import { toggleCharmSelection } from "./selection.js";

export function getVisibleCharms() {
  const searchQuery = viewerState.searchQuery.trim().toLowerCase();
  return viewerState.allCharms.filter((charm) => {
    if (viewerState.activeCategoryName !== null
        && charm.category !== viewerState.activeCategoryName) {
      return false;
    }
    if (viewerState.activeTypeFilter
        && charm.type !== viewerState.activeTypeFilter) {
      return false;
    }
    if (searchQuery) {
      const matchesName = charm.name.toLowerCase().includes(searchQuery);
      const matchesDescription = viewerState.searchInDescriptions
        && charm.description.toLowerCase().includes(searchQuery);
      if (!matchesName && !matchesDescription) return false;
    }
    return true;
  });
}

export function renderCharmList() {
  const listContainer = elementById("charmList");
  const visibleCharms = getVisibleCharms();
  listContainer.innerHTML = "";
  if (!visibleCharms.length) {
    listContainer.innerHTML = `<div class="empty">No charms match.</div>`;
    return;
  }
  const listFragment = document.createDocumentFragment();
  visibleCharms.forEach((charm) => {
    const listItem = document.createElement("div");
    listItem.className =
      "item" + (viewerState.openCharmId === charm.id ? " active" : "");
    const checkedAttribute =
      viewerState.selectedCharmIds.has(charm.id) ? "checked" : "";
    listItem.innerHTML =
      `<input type="checkbox" ${checkedAttribute} data-id="${charm.id}">
       <div><div class="nm">${escapeHtml(charm.name)}</div>
       <div class="sub">${escapeHtml(charm.category)} · ` +
      `${escapeHtml(charm.type || "—")} · p${charm.page}</div></div>`;
    listItem.querySelector("input").onclick = (event) => {
      event.stopPropagation();
      toggleCharmSelection(charm.id, event.target.checked);
    };
    listItem.onclick = () => showCharmDetail(charm.id);
    listFragment.appendChild(listItem);
  });
  listContainer.appendChild(listFragment);
}
