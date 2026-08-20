# Changelog

## 0.26.1 - 2026-08-20

- Fixed the home dashboard's layer picker overflowing its card on mobile
- Fixed the floor plan editor still not fitting the screen on first load in some cases
- Fixed L-shaped stairs rendering with steps crossing through the corner instead of turning
- Fixed rectangular dining table chairs not balancing evenly across the two long sides

## 0.26.0 - 2026-08-17

- Added a "years span" stat card to the works timeline, showing the number of years between the first and last work
- Fixed the works list's title/description cell to clamp to two lines with an ellipsis instead of overflowing
- Replaced the knowledge base expand/collapse-all icon with a clearer chevron-and-bar icon
- Fixed every inventory item save failing with a server error on installs upgraded from an older version

## 0.25.1 - 2026-08-17

- Fixed the home dashboard's chore/inventory/costs/works floor-plan badges appearing oversized instead of scaling down with the widget
- Restyled the home dashboard's floor picker to match the layers dropdown, and removed its non-functional "All floors" option
- Fixed the floor plan editor needing a manual "Reset View" click to show the floor plan correctly on load
- Sorted the chores list by next due date by default
- Sorted the works list by not-yet-done status and most recent date by default
- Moved the works timeline's planned/in-progress/done counts into its legend, keeping only the total cost as a stat tile, and fixed the timeline card stretching taller than its content

## 0.25.0 - 2026-08-16

- Added the ability to type a date directly into any date field, alongside the existing calendar picker
- Added a year-grid view to the calendar picker (click the month/year label) for quickly jumping to a distant year, paged by decade
- Replaced the chore schedule-anchor checkbox with a two-option picker with explanatory captions, plus a live "next due (calculated)" preview
- Fixed the knowledge base sidebar expand/collapse-all icon rendering small and off-center
- Fixed the chore edit modal's footer button order to stay consistent across tabs, moved "Place on map" into the Assignments tab, and put the emoji field on the same row as Name
- Sorted the chore assignment zone picker alphabetically
- Fixed the All/Needs-attention chores list toggle not persisting across in-session navigation
- Doubled the floor plan chore badge size

## 0.24.2 - 2026-08-14

- Fixed the knowledge base autosave indicator to show inside the save button instead of flickering as a separate icon
- Fixed the knowledge base expand/collapse-all and new-page toolbar buttons to be the same size
- Replaced the knowledge base edit icon with a clearer pencil icon styled to match the save button
- Fixed the chore edit modal's Save button being hidden on the Assignments/Media/History tabs
- Fixed the chore assignment row's mark-done/delay/delete buttons splitting across two lines
- Reverted floor plan zone/room labels to always stay centered, undoing the off-center placement for zones containing other rooms
- Fixed a bug where deleting a floor plan wall shared between a zone and a room nested inside it could silently drop the nested room and orphan its chores/inventory/consumables/costs — now shows a confirmation listing the affected room(s) before deleting

## 0.24.1 - 2026-08-13

- Fixed the floor plan editor's mobile zone/opening/furniture panels overflowing off the right edge of the screen, putting the close button out of reach
- Fixed the floor plan editor's mobile Picker and Furniture panels not scrolling on touch
- Fixed a zone containing other zones (e.g. a garden boundary with a shed inside it) intercepting clicks meant for the nested zone underneath — it's now only selectable by tapping its label
- Fixed the home dashboard floor selector to be a proper dropdown, and fixed mobile layers alignment
- Fixed the knowledge base page-tree "toggle all" icon not rotating and the mobile disclosure triangle being too small to tap

## 0.24.0 - 2026-08-12

- Added a "Details" button to floor plan chore pins to open the full chore edit view, not just the small popup
- Fixed room labels for a zone room containing other rooms (e.g. an outdoor zone with a shed inside) overlapping the child room instead of moving to the most open point
- Fixed touch-drag on mobile being hijacked as a page scroll when dragging items from the floor plan's Picker or Furniture panel
- Added a straight/L-shaped variant for stairs furniture
- Fixed the floor plan editor's mobile Edit/View toggle button jumping position when switching modes
- Fixed the knowledge base page-tree expand/collapse icon not clearly showing its state — it now rotates and shows a tooltip
- Changed the knowledge base save-status indicator from text to a spinner/checkmark/warning icon
- Added an Edit icon button to knowledge base pages, alongside double-click-to-edit
- Renamed "Room" to "Zone" throughout the floor plan editor, Chores, Costs, and Inventory (e.g. a garden is a zone, not a room)

## 0.23.0 - 2026-08-12

- Fixed the floor plan editor's mobile Picker button appearing to do nothing when tapped — it's now greyed out until a module layer (Chores, Inventory, Consumables, Costs, or Works) is turned on
- Changed the floor plan editor's mobile Picker and Furniture panels to open as a small popup anchored near the toolbar instead of a full-width panel covering most of the screen, matching the View/Draw/Actions tool groups
- Changed the mobile Picker and Furniture panels to close automatically after placing an item, so the floor plan is immediately visible again

## 0.22.0 - 2026-08-11

- Changed the floor plan editor's mobile toolbar to show bigger, uniform, icon-only buttons for every tool (including the floor and layers pickers) instead of small icons with text labels underneath
- Changed the View, Draw, and Actions tool groups to open as a small popup anchored near the toolbar instead of a full-screen dialog, listing each tool as an icon with its label

## 0.21.0 - 2026-08-11

- Changed the floor plan editor's mobile toolbar to group tools into View, Draw, and Actions icon buttons that open a modal with larger touch targets, instead of a single row requiring horizontal scrolling to reach every tool
- Changed the floor and layers pickers in the floor plan toolbar to icon-only on mobile, freeing up space for the new tool groups
- Added a floating indicator above the mobile toolbar showing the currently active drawing tool, which reopens the relevant tool group when tapped
- Changed the floor plan edit/view mode icon to a slashed pencil in view mode instead of an eye, since the eye icon is now used for the View tools group

## 0.20.1 - 2026-08-11

- Fixed wall, divider, and garden-border drag handles being too small to grab reliably on touchscreens (e.g. iPad) — a slightly imprecise touch missed the handle entirely with no visible feedback, making it look like selection worked but dragging didn't

## 0.20.0 - 2026-08-10

- Fixed the Chores history always showing "Whole house" for a completed chore even when it was assigned to a specific room — "Mark all done" and the floor-plan pin's "All done" action now record which room(s) were actually completed
- Fixed the Chores Planning column showing "Monthly on day N" for a schedule restricted to specific months (e.g. day 20, August only) — it now shows the day plus the actual allowed month(s)
- Added click-to-filter on the Chores KPI tiles and schedule-health chart — click a tile or bar segment to filter the list to that bucket, click again to clear
- Added the ability to set a per-assignment label from the floor-plan pin popup, so multiple assignments of the same chore in the same room (e.g. two windows) can be told apart
- Added an Assignments tab to the chore edit modal for managing a chore's room assignments (view, complete, delay, delete, create) and giving each one an optional label
- Fixed the Chores "mark done" action expanding inline into a note field and date picker, which broke layout and caused horizontal scrolling on mobile — replaced with a modal used consistently across the home dashboard, the chores table, and per-assignment completion
- Fixed the Chores History tab ordering completions by insertion order instead of completion date, so a backdated entry could appear out of order
- Added a view/edit mode toggle to the floor plan editor — view mode hides the editing toolbar and disables drag handles while keeping pan, zoom, and click-to-inspect
- Fixed "Ajouter un étage" (add floor) appearing to do nothing when clicked from the "All floors" overview
- Fixed sliding doors and window orientation not actually saving — the backend was silently dropping both fields
- Fixed long furniture labels overflowing the floating panel instead of truncating, and fixed clicking (not dragging) a furniture item dropping it invisibly behind the toolbar instead of on the visible canvas
- Fixed the floor picker not closing on an outside click, and a partially-closed roller shutter blocking clicks on the window underneath it
- Added a "Garden Border" wall type for marking a garden/plot boundary, rendered as a dashed green line and detected as an enclosed area when drawn as a closed loop
- Fixed the floor plan editor rendering blank on load or floor switch when a floor's content fell outside the default view — the viewport now auto-fits to the floor's content
- Added a dedicated Pan tool to the floor plan toolbar, available in both edit and view mode
- Added a "double" (French) door kind with two independent hinged leaves, and fixed exported floor plan SVGs rendering every door as a plain single leaf regardless of its actual kind
- Added configurable per-item parameters to floor plan furniture — a new Stairs item, chair count for dining/round tables, straight or L-shaped sofas with a choice of corner, and adjustable plank size for decks/terraces
- Added autosave to the Knowledge Base editor, replacing the manual Save/Cancel buttons with a Saving…/Saved status indicator, and changed editing to start on double-click instead of an Edit button
- Added a navigation guard to the Knowledge Base editor so leaving a page (switching pages, other modules, browser back/forward, or closing the tab) waits for a pending autosave to finish first
- Added reopening the last-viewed Knowledge Base page when returning to the module instead of showing an empty placeholder

## 0.19.0 - 2026-08-07

- Added door kinds (hinged, swinging, sliding, garage) and a window in/out side toggle to the floor plan opening panel, each rendered with its own door/window symbol instead of one generic symbol for all doors and windows
- Changed the Home Assistant sensor picker in the opening panel to only show sensors matching the opening type (door/garage-door sensors for doors, window sensors for windows) instead of every binary sensor in the house
- Changed the toolbar above every module's table (Chores, Consumables, Inventory, Works, Costs, Contacts, Properties, Insurance) to fit on one line on mobile — dropdown filters now live behind a filter icon that opens a modal, and the Add button is icon-only
- Changed the KPI/stat row above Chores, Consumables, and Works to wrap stat tiles into fewer rows on mobile instead of stacking one per line

## 0.18.0 - 2026-08-06

- Added the ability to link floor plan windows and doors to Home Assistant door/window sensors — they now show orange on the floor plan when open (and gray if the sensor is unreachable), delivered live over a new "Home Assistant" map layer that's on by default
- Added roller shutter support for windows — link a shutter's Home Assistant cover entity to see its position on the floor plan and open, close, or stop it directly from there
- Added full touch/mobile support across the app: tables hide low-priority columns on narrow screens, the top bar and modals reflow below 480px, floating panels can be dragged and collapse into bottom sheets on mobile, the floor plan canvas supports touch drawing/dragging/panning/pinch-zoom, and drag-and-drop reordering works via touch instead of requiring a mouse

## 0.17.1 - 2026-08-05

- Fixed the chore backdated-completion date picker not honoring the Date Format set in Settings > Localization (always showed "D Month YYYY" instead of your chosen MM/DD/YYYY, DD/MM/YYYY, or YYYY-MM-DD) — this affected every date picker in the app, not just chores
- Fixed the same date picker overlapping the confirm/cancel buttons on the chore mark-done row

## 0.17.0 - 2026-08-04

- Added the ability to log a chore as completed on a past date instead of only "now" — the next-due date only shifts if the backdated entry is the most recent completion on record, so logging an older catch-up entry never disturbs the current schedule
- Changed the Knowledge Base media picker to insert plain markdown instead of raw HTML when embedding a photo or document, so page content stays portable and readable as markdown

## 0.16.0 - 2026-08-03

- Added a fast upload/download path for MCP attachment tools (Claude/AI assistant integrations) — large photos and PDFs used to have to be sent as inline text, which could take minutes to hours; they're now transferred directly, cutting that down to seconds
- Fixed attachment photo/PDF previews not loading in the Works, Inventory, Chores, Costs, and Knowledge Base edit panels, and the House Build task panel — a URL bug meant thumbnails silently failed to appear

## 0.15.0 - 2026-08-02

- Added whole-page scrolling on mobile for Chores, Contacts, Costs, Consumables, Insurance, Inventory, Properties, Works, and Build — previously only the inner table scrolled, leaving the toolbar and charts pinned above it
- Added a collapsible sidebar (tap the menu icon) to the Knowledge Base editor on mobile, freeing up space to actually edit a page
- Renamed "Knowledge Base" to "Wiki" throughout the app
- Fixed an MCP attachment upload with certain filenames (e.g. punctuation stripped down to just a leading-dot extension) silently saving a file that could never be fetched or deleted afterward
- Hardened the Knowledge Base bookmark preview fetch against an SSRF gap that didn't block a shared/carrier-grade-NAT address range

## 0.14.0 - 2026-08-02

- Added web bookmark cards to the Knowledge Base editor — paste a URL to insert a rich preview card (title, description, thumbnail, favicon+domain) instead of a plain link, plus a matching `add_kb_bookmark` MCP tool
- Added MCP tools to upload, delete, and fetch attachments across all 8 attachment-capable modules (Inventory, Chores, Costs, Works, Consumables, KB, Contacts, Properties)
- Moved the Knowledge Base editor's Save/Cancel buttons next to the Edit button at the top of the page, instead of a footer below the editor

## 0.13.0 - 2026-08-01

- Added Owner and Store fields to Inventory items — pick an existing one from the dropdown or type a new name to create it on the spot, no need to visit Settings first
- Added Owner and Store filters and columns to the Inventory list, and management tabs for both under Settings → Categories
- Fixed the Inventory item form's Category field: typing a brand-new category previously didn't actually save it to Settings → Categories, so it silently disappeared next time you opened the list — it now creates the category for real, the same way Owner and Store do

## 0.12.0 - 2026-08-01

- Added a new "Localization" settings category (Settings → Localization) with Date Format, Time Format, and First Day of Week preferences, alongside the existing Language selector — these now control how dates and times render throughout the app, including the date picker's calendar grid
- Added a new "Nth weekday of month/quarter" chore recurrence (e.g. "2nd Tuesday of every month", "last Friday of every quarter"), available in the schedule picker, Donetick import, and the quick-add box
- Fixed a Donetick-imported chore with a "day of the month" recurrence restricted to specific months (e.g. a quarterly service) scheduling almost a year late, because Donetick sends month names as text (e.g. "March") rather than numbers

## 0.11.1 - 2026-07-30

- Fixed a Donetick-imported chore with a "yearly"/"monthly"/"weekly" recurrence showing the wrong interval (e.g. "Every 3 years" instead of "Yearly") when Donetick attached a stray, unused frequency value to the import

## 0.11.0 - 2026-07-30

- Added a per-module "Reset" option in Settings → General to clear one module's data (records and attachments) without deleting the whole home — categories and other shared config are kept
- Fixed the Donetick import showing a generic "Failed" message instead of the actual error (wrong URL, DNS failure, bad token, unreachable server, etc.)

## 0.10.1 - 2026-07-29

- Fixed the release build, which failed after an unrelated upstream dependency published a breaking major version (no user-facing changes; see 0.10.0 below for what's actually in this release)

## 0.10.0 - 2026-07-29

- Added a URL field to the Donetick import (Settings → Integrations) — the server address is no longer hardcoded, and the import is now restricted to admins with SSRF hardening on the URL
- Fixed chores imported from Donetick not showing up in the Chores list by default
- Fixed the floor-plan toolbar disappearing after assigning a chore to "whole house", with no way back to a floor without reloading

## 0.9.1 - 2026-07-27

- Added an optional direct port mapping for the web UI/API (Settings → Add-on → Network), for MCP clients that can't reach the app through Home Assistant's ingress URL

## 0.9.0 - 2026-07-27

- Added an About screen (Settings) showing app version, deployment mode, and whether a newer release is available
- Restyled stat cards across every module (Chores, Inventory, Consumables, Costs, Works, Insurance, Properties, Contacts, Build) onto a shared, consistent chart + stat-card layout
- Fixed the app version showing as "unknown" when running outside the built container image

## 0.8.0 - 2026-07-26

- Added full French translation and app-wide i18n support
- Added a house build tracking module (phases and tasks for new-construction projects)
- Added a contacts module (contractors, suppliers, and providers directory)
- Added an insurance module for tracking policies and renewals
- Fixed a bug where cost/inventory/work/consumable categories and suppliers were shared across homes instead of scoped per home
- Fixed build page layout

## 0.7.1 - 2026-07-22

- Fixed the room panel being hidden and new homes starting without a floor

## 0.7.0 - 2026-07-21

- Added a Properties module for tracking land/house/new-build listings
- Hardened Home Assistant ingress trust handling and fixed an admin authentication edge case

## 0.6.0 - 2026-07-17

- Reworked the Knowledge Base so pages can nest as folders, with icons, live links, and a Trash
- Moved the Donetick import into Settings → Integrations

## 0.5.2 - 2026-07-15

- Fixed the frontend not working when served from a path prefix under Home Assistant ingress

## 0.5.1 - 2026-07-15

- Fixed the add-on icon, panel icon, and repository recognition in Home Assistant
- Fixed static assets requiring authentication

## 0.5.0 - 2026-07-14

- Migrated data persistence to SQLite
- Added sortable tables and chart + stat-card summary layouts across modules
- Extended the activity log to show entries from all users

## 0.4.0 - 2026-07-08

- Added multi-home support, global search, a notification center, scheduled backups, and an activity log
- Added an in-process MCP server exposing the app's tools
- Added a furniture library and improved wall rendering
- Reorganized Settings into a sidebar-navigated panel
- Added a consumables module
- Extended the media gallery to more modules

## 0.3.0 - 2026-06-29

- Baseline add-on release
