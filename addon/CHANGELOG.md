# Changelog

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
