// Entry point: load charm data, populate state, render, and wire controls.
import { viewerState } from "./state.js";
import { elementById } from "./dom-utils.js";
import { renderCategorySidebar } from "./category-sidebar.js";
import { renderCharmList } from "./charm-list.js";
import { showCharmDetail } from "./charm-detail.js";
import { updateSelectionSummary } from "./selection.js";
import { exportAllCharms, exportSelectedCharms } from "./export-controls.js";

// Best-effort load of a pre-parsed file (local dev convenience). The hosted
// app has no such file, so a failure here just means "wait for an upload".
async function loadPreparsedData() {
  const response = await fetch("../data/charms.json");
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

// Upload the chosen PDF, parse it server-side (in memory), and load the result.
async function uploadAndParsePdf(file) {
  setStatus(`Parsing ${file.name}… (first run may take a while)`);
  const formData = new FormData();
  formData.append("pdf", file);
  let response;
  try {
    response = await fetch("parse", { method: "POST", body: formData });
  } catch (networkError) {
    setStatus(`Upload failed: ${networkError.message}`);
    return;
  }
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      message = (await response.json()).error || message;
    } catch (_) { /* non-JSON error body */ }
    setStatus(`Could not parse PDF: ${message}`);
    return;
  }
  loadCharmData(await response.json());
}

function setStatus(message) {
  elementById("charmDetail").innerHTML =
    `<div class="placeholder">${message}</div>`;
}

function populateStateFrom(charmData) {
  viewerState.allCharms = charmData.charms;
  viewerState.categoryNames = charmData.categories;
  viewerState.charmsById.clear();
  charmData.charms.forEach(
    (charm) => viewerState.charmsById.set(charm.id, charm));
  viewerState.abilityCategoryNames = charmData.categories.filter(
    (name) => !/ Style$/.test(name) && !/ Circle Spells$/.test(name));
  viewerState.martialArtsCategoryNames =
    charmData.categories.filter((name) => / Style$/.test(name));
  viewerState.sorceryCategoryNames =
    charmData.categories.filter((name) => / Circle Spells$/.test(name));
  // Reset per-dataset view state (relevant when a new PDF is uploaded).
  viewerState.selectedCharmIds.clear();
  viewerState.activeCategoryName = null;
  viewerState.openCharmId = null;
  viewerState.searchQuery = "";
}

function populateTypeFilter() {
  const typeFilterSelect = elementById("typeFilterSelect");
  typeFilterSelect.innerHTML = `<option value="">All types</option>`;
  const charmTypes = [...new Set(
    viewerState.allCharms.map((charm) => charm.type).filter(Boolean))].sort();
  charmTypes.forEach((charmType) => {
    const option = document.createElement("option");
    option.value = charmType;
    option.textContent = charmType;
    typeFilterSelect.appendChild(option);
  });
}

// Load a parsed dataset (from upload or the pre-parsed file) and render it.
function loadCharmData(charmData) {
  populateStateFrom(charmData);
  elementById("searchInput").value = "";
  elementById("dataSummary").textContent =
    `${viewerState.allCharms.length} charms · ` +
    `${viewerState.categoryNames.length} categories`;
  populateTypeFilter();
  renderCategorySidebar();
  renderCharmList();
  updateSelectionSummary();
  setStatus("Select a charm to view its details.");
  openCharmFromUrlHash();
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
  elementById("pdfInput").onchange = (event) => {
    const file = event.target.files[0];
    if (file) uploadAndParsePdf(file);
    event.target.value = "";  // allow re-uploading the same file
  };
  updateSelectionSummary();
}

function openCharmFromUrlHash() {
  const charmIdInHash = decodeURIComponent(location.hash.slice(1));
  if (charmIdInHash && viewerState.charmsById.has(charmIdInHash)) {
    showCharmDetail(charmIdInHash);
  }
}

async function startViewer() {
  wireControls();
  try {
    loadCharmData(await loadPreparsedData());
  } catch (_) {
    // No pre-parsed data (the normal case when hosted): prompt for a PDF.
    setStatus("Upload your Exalted 3e core rulebook PDF to begin "
      + "(top-left button). It is parsed in memory and never stored.");
  }
}

startViewer();
