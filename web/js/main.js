// Entry point: load charm data, populate state, render, and wire controls.
import { viewerState } from "./state.js";
import { elementById } from "./dom-utils.js";
import { renderCategorySidebar } from "./category-sidebar.js";
import { renderCharmList } from "./charm-list.js";
import { showCharmDetail } from "./charm-detail.js";
import { updateSelectionSummary } from "./selection.js";
import { exportAllCharms, exportSelectedCharms } from "./export-controls.js";

async function loadCharmData() {
  const response = await fetch("../data/charms.json");
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function populateStateFrom(charmData) {
  viewerState.allCharms = charmData.charms;
  viewerState.categoryNames = charmData.categories;
  charmData.charms.forEach(
    (charm) => viewerState.charmsById.set(charm.id, charm));
  viewerState.abilityCategoryNames =
    charmData.categories.filter((name) => !/ Style$/.test(name));
  viewerState.martialArtsCategoryNames =
    charmData.categories.filter((name) => / Style$/.test(name));
}

function populateTypeFilter() {
  const charmTypes = [...new Set(
    viewerState.allCharms.map((charm) => charm.type).filter(Boolean))].sort();
  const typeFilterSelect = elementById("typeFilterSelect");
  charmTypes.forEach((charmType) => {
    const option = document.createElement("option");
    option.value = charmType;
    option.textContent = charmType;
    typeFilterSelect.appendChild(option);
  });
}

function wireControls() {
  elementById("searchInput").oninput = (event) => {
    viewerState.searchQuery = event.target.value;
    renderCharmList();
  };
  elementById("searchDescriptionsCheckbox").onchange = (event) => {
    viewerState.searchInDescriptions = event.target.checked;
    renderCharmList();
  };
  elementById("typeFilterSelect").onchange = (event) => {
    viewerState.activeTypeFilter = event.target.value;
    renderCharmList();
  };
  elementById("clearSelectionButton").onclick = () => {
    viewerState.selectedCharmIds.clear();
    updateSelectionSummary();
    renderCharmList();
    renderCategorySidebar();
  };
  elementById("exportAllButton").onclick = exportAllCharms;
  elementById("exportSelectedButton").onclick = exportSelectedCharms;
  updateSelectionSummary();
}

function openCharmFromUrlHash() {
  const charmIdInHash = decodeURIComponent(location.hash.slice(1));
  if (charmIdInHash && viewerState.charmsById.has(charmIdInHash)) {
    showCharmDetail(charmIdInHash);
  }
}

async function startViewer() {
  let charmData;
  try {
    charmData = await loadCharmData();
  } catch (error) {
    elementById("charmDetail").innerHTML =
      `<div class="placeholder">Could not load ../data/charms.json ` +
      `(${error.message}).<br>` +
      `Run the parser, then serve with <code>python3 -m http.server</code>.</div>`;
    return;
  }
  populateStateFrom(charmData);
  elementById("dataSummary").textContent =
    `${viewerState.allCharms.length} charms · ` +
    `${viewerState.categoryNames.length} categories`;
  populateTypeFilter();
  renderCategorySidebar();
  renderCharmList();
  wireControls();
  openCharmFromUrlHash();
}

startViewer();
