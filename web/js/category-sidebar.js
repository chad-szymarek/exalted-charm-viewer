// The left sidebar: "All charms" plus ability and martial-arts categories.
import { viewerState } from "./state.js";
import { elementById, escapeHtml } from "./dom-utils.js";
import { renderCharmList } from "./charm-list.js";

function charmCountInCategory(categoryName) {
  return viewerState.allCharms.filter(
    (charm) => charm.category === categoryName).length;
}

function selectCategory(categoryName) {
  viewerState.activeCategoryName = categoryName;
  renderCategorySidebar();
  renderCharmList();
}

export function renderCategorySidebar() {
  const sidebar = elementById("categorySidebar");
  sidebar.innerHTML = "";

  const allCharmsEntry = document.createElement("div");
  allCharmsEntry.className =
    "cat" + (viewerState.activeCategoryName === null ? " active" : "");
  allCharmsEntry.innerHTML =
    `<span>All charms</span><span class="n">${viewerState.allCharms.length}</span>`;
  allCharmsEntry.onclick = () => selectCategory(null);
  sidebar.appendChild(allCharmsEntry);

  const appendCategoryGroup = (groupLabel, categoryNames) => {
    if (!categoryNames.length) return;
    const groupHeading = document.createElement("div");
    groupHeading.className = "cat group";
    groupHeading.textContent = groupLabel;
    sidebar.appendChild(groupHeading);
    categoryNames.forEach((categoryName) => {
      const categoryEntry = document.createElement("div");
      categoryEntry.className =
        "cat" + (viewerState.activeCategoryName === categoryName ? " active" : "");
      categoryEntry.innerHTML =
        `<span>${escapeHtml(categoryName)}</span>` +
        `<span class="n">${charmCountInCategory(categoryName)}</span>`;
      categoryEntry.onclick = () => selectCategory(categoryName);
      sidebar.appendChild(categoryEntry);
    });
  };
  appendCategoryGroup("Abilities", viewerState.abilityCategoryNames);
  appendCategoryGroup("Martial Arts", viewerState.martialArtsCategoryNames);
}
