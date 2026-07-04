// Charm selection (the checkbox set) and the header's selection summary.
import { viewerState } from "./state.js";
import { elementById } from "./dom-utils.js";

export function toggleCharmSelection(charmId, isSelected) {
  if (isSelected) {
    viewerState.selectedCharmIds.add(charmId);
  } else {
    viewerState.selectedCharmIds.delete(charmId);
  }
  updateSelectionSummary();
}

export function updateSelectionSummary() {
  const selectedCount = viewerState.selectedCharmIds.size;
  elementById("selectionSummary").textContent = `${selectedCount} selected`;
  elementById("exportSelectedButton").disabled = selectedCount === 0;
}
