// The left sidebar: "All charms" plus ability and martial-arts categories.
import { viewerState } from "./state.js";
import { elementById, escapeHtml } from "./dom-utils.js";
import { renderCharmList } from "./charm-list.js";

function charmCountInCategory(categoryName) {
  return viewerState.allCharms.filter(
    (charm) => charm.category === categoryName).length;
}

function selectedCountInCategory(categoryName) {
  return viewerState.allCharms.filter(
    (charm) => charm.category === categoryName
      && viewerState.selectedCharmIds.has(charm.id)).length;
}

// The counts shown on the right of a sidebar row: a gold "selected" badge
// (only when > 0) followed by the total charm count.
function countsHtml(selectedCount, totalCount) {
  const selectedBadge = selectedCount
    ? `<span class="selcount">${selectedCount}</span>` : "";
  return `<span class="counts">${selectedBadge}` +
    `<span class="n">${totalCount}</span></span>`;
}

function selectCategory(categoryName) {
  viewerState.activeCategoryName = categoryName;
  renderCategorySidebar();
  renderCharmList();
}

export function renderCategorySidebar() {
  const sidebar = elementById("categorySidebar");
  sidebar.innerHTML = "";

  const totalSelected = viewerState.selectedCharmIds.size;
  const allCharmsEntry = document.createElement("div");
  allCharmsEntry.className = "cat"
    + (viewerState.activeCategoryName === null ? " active" : "")
    + (totalSelected ? " has-selection" : "");
  allCharmsEntry.innerHTML = `<span>All charms</span>`
    + countsHtml(totalSelected, viewerState.allCharms.length);
  allCharmsEntry.onclick = () => selectCategory(null);
  sidebar.appendChild(allCharmsEntry);

  const appendCategoryGroup = (groupLabel, categoryNames) => {
    if (!categoryNames.length) return;
    const isCollapsed = viewerState.collapsedGroups.has(groupLabel);
    const groupSelected = categoryNames.reduce(
      (sum, name) => sum + selectedCountInCategory(name), 0);
    const groupHeading = document.createElement("div");
    groupHeading.className = "cat group" + (groupSelected ? " has-selection" : "");
    const groupBadge = groupSelected
      ? `<span class="selcount">${groupSelected}</span>` : "";
    groupHeading.innerHTML =
      `<span>${escapeHtml(groupLabel)}</span>` +
      `<span class="counts">${groupBadge}` +
      `<span class="caret">${isCollapsed ? "▸" : "▾"}</span></span>`;
    groupHeading.onclick = () => {
      if (isCollapsed) viewerState.collapsedGroups.delete(groupLabel);
      else viewerState.collapsedGroups.add(groupLabel);
      renderCategorySidebar();
    };
    sidebar.appendChild(groupHeading);
    if (isCollapsed) return;
    categoryNames.forEach((categoryName) => {
      const selectedCount = selectedCountInCategory(categoryName);
      const categoryEntry = document.createElement("div");
      categoryEntry.className = "cat"
        + (viewerState.activeCategoryName === categoryName ? " active" : "")
        + (selectedCount ? " has-selection" : "");
      categoryEntry.innerHTML =
        `<span>${escapeHtml(categoryName)}</span>` +
        countsHtml(selectedCount, charmCountInCategory(categoryName));
      categoryEntry.onclick = () => selectCategory(categoryName);
      sidebar.appendChild(categoryEntry);
    });
  };
  appendCategoryGroup("Abilities", viewerState.abilityCategoryNames);
  appendCategoryGroup("Martial Arts", viewerState.martialArtsCategoryNames);
  appendCategoryGroup("Sorcery", viewerState.sorceryCategoryNames);
}
