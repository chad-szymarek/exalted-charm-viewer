// Shared viewer state. Every module reads and writes this single object;
// rendering modules re-render from it after each change.
export const viewerState = {
  allCharms: [],
  charmsById: new Map(),
  categoryNames: [],            // ordered, as emitted by the parser
  abilityCategoryNames: [],     // Chapter Six abilities
  martialArtsCategoryNames: [], // Chapter Seven "... Style" categories
  sorceryCategoryNames: [],     // sorcery "... Circle Spells" categories
  selectedCharmIds: new Set(),
  collapsedGroups: new Set(),   // group labels hidden in the sidebar
  activeCategoryName: null,     // null = all categories
  activeTypeFilter: "",         // "" = all types
  searchQuery: "",
  searchInDescriptions: false,
  openCharmId: null,            // charm shown in the detail pane
};
