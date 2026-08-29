// Module-level (not component-level) so the Chores list's "needs attention"
// filter survives navigating away and back within a session --
// ChoresPage is unmounted/remounted by the router on every route change.
export type ChoreDueFilter = "all" | "attention";

export const choreFilterState = $state<{ dueFilter: ChoreDueFilter }>({ dueFilter: "all" });
