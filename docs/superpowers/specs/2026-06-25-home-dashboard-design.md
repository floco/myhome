# Home Dashboard Design

## Purpose

The app currently has no single overview page — the floor-plan editor is the default landing page, and each module (chores, costs, inventory, works) is a separate full-page view. Users want a "birds eye view" homepage that surfaces the most relevant status from every module at a glance, since this will be the page they see most often.

## Routing changes

- `#/` now renders the new `HomePage` (the dashboard). It becomes the default landing page.
- The floor-plan editor moves from `#/` to a new route, `#/plan`.
- All other routes are unchanged: `#/chores`, `#/chores/manage`, `#/inventory`, `#/consumables`, `#/works`, `#/costs`, `#/settings`.
- `NavMenu.svelte` gets a new "Home" entry at the top of the list, linking to `#/`. The existing floor-plan nav entry now points to `#/plan`.

## Page layout

New component: `packages/editor/src/lib/components/HomePage.svelte`.

- Two-column layout at desktop widths: left column `2fr`, right column `1fr`.
- Below the app's existing mobile breakpoint, the layout collapses to a single column, in reading order: Map, Chores, Costs, Inventory, Works.
- Left column (top to bottom): Map widget, Chores widget.
- Right column (top to bottom): Costs widget, Inventory widget, Works widget.
- Each widget is wrapped in the shared `Card` component for visual consistency with the rest of the app.
- Cards size to their content — no internal scrolling within a card. The page itself scrolls vertically if total content exceeds the viewport.
- Widgets are clickable shortcuts into their full module page. Interactive sub-elements within a widget (chore checkmarks, floor switcher, layer dropdown) call `stopPropagation()` so they don't trigger the widget's navigation.

## Widget: Map (`HomeMapWidget.svelte`)

A read-only view of the floor plan, reusing existing pieces:

- **`FloorSwitcher`** (reused as-is) — defaults to the first floor on load.
- **`LayersDropdown`** (reused as-is) — defaults to the `chores` layer active; user can toggle layers within the widget itself.
- **`Canvas`** in read-only mode — `tool="select"`, no draw/edit event handlers wired up. `Canvas` gains a new `showGrid` boolean prop (default `true`, preserving current behavior everywhere else) that the widget sets to `false` to suppress the `Grid` sub-component.
- **Auto-fit viewport** — a fixed `ViewportState` computed to fit the current floor's bounding box into the widget's width/height. No pan/zoom handlers are attached. Recomputed when the floor changes or the widget resizes.
- **Pin rendering** — pins for the active layer(s) render as plain markers with no click-to-popup interaction (unlike the full editor). Clicking the canvas area (outside the floor switcher / layer dropdown) navigates to `#/plan`.

### Pin logic extraction

Per-layer pin-position computation currently lives inline in `App.svelte`'s template (alongside click handlers that open popups). This needs to be extracted into small, pure, reusable functions — one per layer (chores, inventory, costs, works) — that take floor/store data and return pin positions + display data. Both `App.svelte` (full editor, with popups) and `HomeMapWidget` (no popups) consume the same extracted functions. This avoids duplicating/diverging pin logic between the two surfaces.

## Widget: Chores (`HomeChoresWidget.svelte`)

- **Stat row**: active assignment count, overdue count, on-track percentage. Reuses `choreStore`'s existing `getProgress`/`getColor` methods.
- **Top-5 list**: the 5 most urgent assignments (same urgency sort as `ChoreListPage` — ascending by progress percentage), each showing emoji, name, due-date label, and a quick-complete checkmark.
- **Quick-complete**: clicking the checkmark opens an inline optional-notes input with confirm/cancel, then calls `store.completeAssignment(id, notes)` — identical behavior to `ChoreListPage`.
- To avoid duplicating this row markup and completion flow, extract a shared `ChoreRow.svelte` component (emoji, name, due label, checkmark → confirm/cancel) used by both `ChoreListPage` and `HomeChoresWidget`.
- Clicking the widget body (outside row controls) navigates to `#/chores`.

## Widget: Costs (`HomeCostsWidget.svelte`)

- Renders a category-breakdown donut for the last complete year, using `costsStore`'s existing `breakdownLastCompleteYear(categories)`.
- The SVG donut-drawing logic currently lives inside `CostsPage.svelte`. Extract it into a reusable `DonutChart.svelte` component (props: array of `{ value, color, label }` segments) so both `CostsPage` and this widget render from the same code.
- No trend/bar chart in this widget — donut only.
- Clicking navigates to `#/costs`.

## Widget: Inventory (`HomeInventoryWidget.svelte`)

- Renders a pie chart (reusing `DonutChart.svelte`) plus a per-category item-count list, computed by grouping `inventoryStore.items` by `category`.
- This is new computation, not extracted from existing code — inventory currently has no chart anywhere in the app.
- Clicking navigates to `#/inventory`.

## Widget: Works (`HomeWorksWidget.svelte`)

- Stat tiles: counts by status (planned / in progress / done) and total cost, computed from `worksStore.works`.
- A short list (top 5) of the most recent works, sorted by date.
- Clicking navigates to `#/works`.

## Out of scope

- Consumables and Settings have no dashboard widget (Consumables is a placeholder page with no meaningful data yet; Settings has no visual summary to show).
- No live/real-time updates beyond the app's existing reactive store behavior — widgets reflect current store state the same way every other page does.
- No customization (reordering, hiding widgets) — layout and widget set are fixed for this iteration.
