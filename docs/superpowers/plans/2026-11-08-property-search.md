# AI Property Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scheduled AI search for land/houses. myhome stores named searches, de-duplicates and triages
suggestions, and emails digests via Brevo. A separate public runner repo executes the searches with
headless Claude Code on the user's Pro plan.

**Architecture:** myhome gets 5 new home-scoped SQL tables and a provider-neutral runner API
(`claim` / `complete` / `fail`). "Due" is computed lazily inside `claim`, so no search scheduler loop
is needed. The only new loop is a daily retention cleanup. The runner (`floco/property-search-runner`)
is a cron-driven Python CLI ported from `floco/jobsearch`'s `agent.py`.

**Tech Stack:** FastAPI + SQLAlchemy Core + SQLite, httpx (Brevo), respx (tests); Svelte 5 +
svelte-i18n + vitest; runner: Python 3 stdlib + httpx + pytest.

**Spec:** `docs/superpowers/specs/2026-11-08-property-search-design.md`

## Global Constraints

- Every new table has `home_id` FK → `homes.id ON DELETE CASCADE`. Every query filters by `home_id`.
- No myhome code names a provider. `provider` is only an opaque string coming from the runner.
- The Brevo API key is never returned by any GET (it returns `brevoApiKeySet: bool`). Only admins can read or write the property-search config.
- Every new UI string goes in both `src/lib/locales/en.json` and `fr.json`, under the `propertySearch.*` namespace.
- Search time `HH:MM` is evaluated in `ZoneInfo(os.environ["TZ"])`, falling back to UTC if unset or invalid.
- Defaults: `maxResultsPerRun=10`, `maxListingAgeDays=7`, `retentionDays=30`. Stale running run = 2 h. Usage-limit retries per slot = 3. Run history kept 90 days. Seen list sent to the runner = last 300.
- Backend tests: `cd packages/backend && python -m pytest <file> -q`. Frontend: `cd packages/editor && npx vitest run <file>`.
- Work happens in a worktree branch `property-search` (create it per superpowers:using-git-worktrees, and symlink `node_modules` per the worktree-workspace memory).

## Review Focus

1. **Two runner ticks at once** (cron overlap, or two runners): the second `claim` must not get the same search. The test goes in Task 4: `test_claim_twice_returns_204_second_time`.
2. **The runner returns garbage**: a listing without a URL, a non-numeric price, or a `publishedAt` that isn't a date. Ingest must skip that item and keep the rest, and must not 500. Task 4: `test_complete_skips_malformed_listings`.
3. **The same listing twice in one batch** (Claude repeats itself): store it once. Task 4: `test_complete_dedups_within_batch`.
4. **Brevo down or key wrong**: the run must still be recorded as succeeded with its suggestions, and the email error logged and shown on the run (`emailError`). Task 5: `test_complete_survives_brevo_failure`.
5. **A search created at 10:00 with daily time 08:00** must not fire immediately for today's already-passed slot. It first runs tomorrow, or now via Run now. Task 2: `test_slot_before_creation_not_due`.

---

## File Structure

**myhome backend** (`packages/backend/src/myhome/`)
- `schema.py`: add tables `property_searches`, `property_suggestions`, `property_seen`, `property_search_runs`, `property_search_config`.
- `models_property_search.py`: pydantic models (new).
- `property_search_dedup.py`: `url_key`, `fingerprint` (pure, new).
- `property_search_schedule.py`: `local_now`, `latest_slot`, `is_due` (pure, new).
- `persistence_property_search.py`: all DB access for the 5 tables (new).
- `property_search_ingest.py`: `claim_next`, `complete_run`, `fail_run` (new).
- `property_search_email.py`: `render_digest`, `render_failure`, `send_brevo` (new).
- `property_search_cleanup.py`: `cleanup_home`, `property_search_cleanup_loop` (new).
- `routes/property_search.py`: user routes + runner routes (new). Register in `main.py`.
- `main.py`: include the router, start the cleanup loop in `_lifespan`.
- `persistence_properties.py`: `reset_properties` also clears property-search data.

**myhome frontend** (`packages/editor/src/lib/`)
- `propertySearchStore.svelte.ts` (new).
- `components/PropertySuggestionsTab.svelte` (new): inbox list and actions.
- `components/PropertySearchesModal.svelte` (new): list plus edit form for searches.
- `components/PropertiesPage.svelte`: add Tabs (Properties | Suggestions with badge).
- `components/settings/SettingsPropertySearch.svelte` (new). `SettingsPage.svelte`: new adminOnly group `propertySearch` with icon 🔎.
- `locales/en.json`, `locales/fr.json`.
- Wherever `propertiesStore` is created and passed to `PropertiesPage` (grep `createPropertiesStore(`): create and pass `propertySearchStore` the same way.

**runner** (`/projects/property-search-runner/`, new public repo)
- `propertysearch/agent.py` (ported from jobsearch), `propertysearch/api.py`, `propertysearch/main.py`, `propertysearch/config.py`, `agent_prompt.md`, `run.sh`, `config/settings.env.example`, `README.md`, `tests/`.

---

### Task 1: Tables, models, persistence

**Files:**
- Modify: `packages/backend/src/myhome/schema.py` (after `properties` table)
- Create: `packages/backend/src/myhome/models_property_search.py`, `packages/backend/src/myhome/persistence_property_search.py`
- Test: `packages/backend/tests/test_property_search_persistence.py`

**Interfaces — Produces:**

```python
# models_property_search.py
Frequency = Literal["daily", "weekly", "monthly"]
SuggestionStatus = Literal["new", "pinned", "accepted", "rejected"]
RunStatus = Literal["running", "succeeded", "failed", "usage_limited"]

class PropertySearch(BaseModel):
    id: str; name: str; prompt: str; enabled: bool = True
    frequency: Frequency = "daily"; time: str = "08:00"; dayOfWeek: int = 1; dayOfMonth: int = 1
    maxResultsPerRun: int = 10; maxListingAgeDays: int = 7
    runRequestedAt: str | None = None; createdAt: str
    lastRunAt: str | None = None; lastRunStatus: RunStatus | None = None; lastRunError: str | None = None
class PropertySearchCreate(BaseModel): # same editable fields, no id/createdAt/last*/runRequestedAt
class PropertySearchUpdate(BaseModel): # all editable fields optional

class PropertySuggestion(BaseModel):
    id: str; searchId: str; runId: str; title: str
    type: Literal["land","house","new_build"] | None = None
    price: float | None = None; currency: str | None = None
    landSize: float | None = None; builtSize: float | None = None
    bedrooms: int | None = None; bathrooms: int | None = None
    location: str = ""; sourceSite: str = ""; listingUrl: str; imageUrl: str | None = None
    publishedAt: str | None = None; reason: str = ""
    status: SuggestionStatus = "new"; createdAt: str; acceptedPropertyId: str | None = None

class SearchUsage(BaseModel):
    provider: str = ""; tokensByModel: dict[str, int] = {}; totalTokens: int = 0
    quotas: list[QuotaUsage] = []        # QuotaUsage(label: str, usedPct: int | None)

class PropertySearchRun(BaseModel):
    id: str; searchId: str; slot: str; startedAt: str; finishedAt: str | None = None
    status: RunStatus; error: str | None = None; emailError: str | None = None
    sites: list[str] = []; searchQueries: list[str] = []; usage: SearchUsage | None = None
    receivedCount: int = 0; newCount: int = 0; duplicateCount: int = 0

class PropertySearchConfig(BaseModel):   # stored; never returned as-is
    retentionDays: int = 30; brevoApiKey: str = ""; senderEmail: str = ""; senderName: str = "My Home"
    recipients: list[str] = []; appBaseUrl: str = ""
class PropertySearchConfigOut(BaseModel):  # GET shape: all fields except brevoApiKey, plus brevoApiKeySet: bool
class PropertySearchConfigUpdate(BaseModel):  # all optional; brevoApiKey "" means "keep existing"
```

Persistence functions (`persistence_property_search.py`). Each one opens its own `engine.begin()`/`connect()`:
`list_searches(home_id) -> list[PropertySearch]`, `get_search(home_id, id) -> PropertySearch | None`,
`insert_search(home_id, s)`, `update_search(home_id, s)`, `delete_search(home_id, id) -> bool` (cascades its suggestions and runs; `property_seen` rows stay),
`list_suggestions(home_id, status: list[str] | None = None) -> list[PropertySuggestion]` (newest first),
`get_suggestion`, `insert_suggestions(home_id, items)`, `set_suggestion_status(home_id, id, status, accepted_property_id=None) -> bool`,
`seen_keys(home_id) -> tuple[set[str], set[str]]` (urlKeys, fingerprints), `add_seen(home_id, rows: list[tuple[str, str|None]])`,
`recent_seen(home_id, limit=300) -> list[dict]` (`{url, title}` from suggestions, newest first),
`insert_run`, `update_run`, `get_run(home_id, run_id)`, `find_run(run_id) -> tuple[str, PropertySearchRun] | None` (across homes),
`list_runs(home_id, search_id, limit=20)`, `load_config(home_id) -> PropertySearchConfig`, `save_config(home_id, cfg)`,
`reset_property_search(home_id)` (deletes all 5 tables' rows for the home).

Tables: columns mirror the models in snake_case. List/dict fields go into `Text` JSON columns. `property_seen` has PK `(home_id, url_key)`, a `fingerprint` column (nullable, indexed) and `first_seen_at`. `property_search_config` has PK `home_id`, and `recipients` stored as JSON.

- [ ] **Step 1: Write failing tests**: `test_search_roundtrip` (insert → get → equal), `test_searches_scoped_by_home` (two homes, `list_searches` returns only own), `test_delete_search_keeps_seen` (add_seen, delete_search, `seen_keys` still contains the key), `test_config_defaults` (`load_config` on fresh home == `PropertySearchConfig()`), `test_suggestion_status_update`, `test_reset_clears_everything`.
- [ ] **Step 2:** Run `python -m pytest tests/test_property_search_persistence.py -q`. Expect FAIL (import error).
- [ ] **Step 3:** Implement the tables, models and persistence.
- [ ] **Step 4:** Run again. Expect PASS. Run `python -m pytest tests/test_db.py tests/test_migrations.py -q` to confirm `create_all` is still fine.
- [ ] **Step 5:** Commit: `feat(property-search): tables, models, persistence`.

### Task 2: Pure helpers: dedup keys and schedule

**Files:**
- Create: `property_search_dedup.py`, `property_search_schedule.py`
- Test: `tests/test_property_search_dedup.py`, `tests/test_property_search_schedule.py`

**Interfaces — Produces:**
- `url_key(url: str) -> str`: lowercases the scheme and host, strips a leading `www.`, drops the fragment and the query params whose name starts with `utm_` or is in `{fbclid, gclid, ref, source}`, sorts the remaining params, and strips the trailing `/` from the path.
- `fingerprint(type: str | None, price: float | None, land: float | None, built: float | None, location: str) -> str | None`: returns `None` unless `price` and at least one of `land`/`built` are set. Otherwise it returns `f"{type or '?'}|{round(price, -3)}|{round(land or 0, -1)}|{round(built or 0)}|{norm(location)}"`, where `norm` lowercases, strips accents (`unicodedata` NFKD), keeps only `[a-z0-9 ]`, and takes the first word ≥ 3 chars (the town).
- `local_now() -> datetime`: tz-aware, using `TZ` (fallback UTC).
- `latest_slot(s: PropertySearch, now: datetime) -> datetime | None`: the most recent scheduled datetime ≤ `now` (looking back ≤ 62 days) whose date matches the frequency (reuse `backup_scheduler._should_run_today(frequency, dayOfWeek, dayOfMonth, d)`) at `s.time`. Returns `None` if that slot is before `s.createdAt`.
- `is_due(s, runs_for_slot: list[PropertySearchRun], now) -> tuple[bool, str | None]`: returns `(True, "manual:"+s.runRequestedAt)` if `runRequestedAt` is set. Otherwise it returns `(True, slot.isoformat())` when `s.enabled`, the slot exists, no run for the slot is `succeeded`/`failed`/`running`, and fewer than 3 are `usage_limited`. Else it returns `(False, None)`.

- [ ] **Step 1: Failing tests.**
  - `test_url_key_strips_tracking`: `url_key("https://WWW.Nepremicnine.net/oglasi/x/?utm_source=a&id=5#top") == "https://nepremicnine.net/oglasi/x?id=5"`.
  - `test_fingerprint_none_when_sparse`: `fingerprint("land", None, 800, None, "Novo Mesto") is None`.
  - `test_fingerprint_matches_across_sites`: `fingerprint("land", 149_500, 812, None, "Novo mesto, Slovenija") == fingerprint("land", 150_000, 808, None, "NOVO MESTO")`.
  - `test_slot_before_creation_not_due`: created 10:00 today with time 08:00 means no slot, so not due.
  - `test_daily_due_after_time`, `test_not_due_when_slot_succeeded`.
  - `test_usage_limited_retries_capped_at_3`.
  - `test_weekly_missed_slot_caught_up`: the slot was 3 days ago, no run, so it is due with that slot.
  - `test_run_requested_overrides_disabled`.
  - `test_local_now_uses_tz_env`: monkeypatch `TZ=Europe/Brussels`, so the offset is +01:00 or +02:00.
- [ ] **Step 2:** Run. Expect FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expect PASS.
- [ ] **Step 5:** Commit: `feat(property-search): dedup keys and schedule helpers`.

### Task 3: User-facing routes (searches, suggestions, config)

**Files:**
- Create: `routes/property_search.py`. Modify: `main.py` (include the router).
- Test: `tests/test_property_search_routes.py`

**Interfaces — Consumes:** Task 1 persistence. Accept uses `load_properties`/`save_properties` and `Property` from `models_properties`.
**Produces (HTTP):**
- `GET/POST /api/homes/{home_id}/property-searches`, `PUT/DELETE /api/homes/{home_id}/property-searches/{id}`. POST sets `createdAt = local_now().isoformat()`. Validation: `time` matches `^\d{2}:\d{2}$`, `1 ≤ maxResultsPerRun ≤ 50`, `1 ≤ maxListingAgeDays ≤ 365`, `name`/`prompt` non-empty, otherwise 422.
- `POST /api/homes/{home_id}/property-searches/{id}/run-now` returns 204 and sets `runRequestedAt`.
- `GET /api/homes/{home_id}/property-searches/{id}/runs` returns `list[PropertySearchRun]`.
- `GET /api/homes/{home_id}/property-suggestions?status=new,pinned` (default `new,pinned`) returns `list[PropertySuggestion]`.
- `POST /api/homes/{home_id}/property-suggestions/{id}/accept` returns 201 with the `Property`. It creates a Property with `name=title`, `emoji` = 🌳 for land else 🏠, `type = s.type or "land"`, `status="watching"`, `address=location`, `price`, sizes, beds, baths, `listingUrl`, and `notes = f"{reason}\n\nSource: {sourceSite}" + (f"\nCurrency: {currency}" if currency else "")`. It then sets the suggestion `accepted` with `acceptedPropertyId`, and logs activity `("properties","create",name,id)`.
- `POST .../{id}/reject` and `POST .../{id}/pin` (toggles `new` ↔ `pinned`) return 204, or 404 when missing.
- `GET/PUT /api/homes/{home_id}/property-search-config` use `require_auth("admin")`. GET returns `PropertySearchConfigOut`. On PUT, `brevoApiKey == ""` or missing keeps the stored key, and `recipients` are each validated to contain `@` (422 otherwise).
- `POST /api/homes/{home_id}/property-search-config/test-email` (admin) calls `send_brevo` (Task 5) with a fixed sample. Returns 204, or 502 with Brevo's message. *Write this endpoint in Task 5.*

- [ ] **Step 1: Failing tests:**
  - `test_create_and_list_search`, `test_create_search_validates_time` (422 for `"8h"`).
  - `test_run_now_sets_flag`.
  - `test_accept_creates_property_and_hides_suggestion`: insert a suggestion via persistence, accept it, then `GET /properties` has 1 item with `status == "watching"` and `listingUrl`, and the suggestions list is empty.
  - `test_reject_and_pin`.
  - `test_config_get_masks_key`: PUT `{"brevoApiKey":"xkeysib-1"}`, GET has `brevoApiKeySet == True` and no `brevoApiKey` key.
  - `test_config_put_empty_key_keeps_existing`.
  - `test_config_requires_admin`: the normal user's client gets 403. Build the normal client like `ro_client`, logging in as `normaluser`.
  - `test_ro_user_cannot_create_search`: 403.
- [ ] **Step 2:** Run. Expect FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expect PASS.
- [ ] **Step 5:** Commit: `feat(property-search): search/suggestion/config routes`.

### Task 4: Runner API and ingest

**Files:**
- Create: `property_search_ingest.py`. Modify: `routes/property_search.py`.
- Test: `tests/test_property_search_runner_api.py`

**Interfaces — Consumes:** Tasks 1–2. **Produces:**
- `claim_next(now: datetime) -> dict | None`. Iterates `load_homes().homes` and their searches (ordered by `createdAt`). First it marks any `running` run older than 2 h as `failed` ("stale"). It then picks the first search where `is_due` holds, inserts a `running` run with that slot, and clears `runRequestedAt` if the slot is manual, all inside one `engine.begin()` transaction. The `is_due` re-check happens inside the same transaction, so a concurrent claim sees the `running` row. It returns `{runId, homeId, searchId, name, prompt, maxResultsPerRun, maxListingAgeDays, today: now.date().isoformat(), seen: recent_seen(home_id)}`.
- `complete_run(run_id, body: RunnerComplete) -> dict` with `RunnerComplete(listings: list[dict], sitesQueried: list[str] = [], searchQueries: list[str] = [], usage: SearchUsage | None = None)`. Each listing dict is validated individually into `PropertySuggestion` fields (bad items are skipped and counted in `receivedCount`). Items are dropped when `publishedAt` parses and is older than `today - maxListingAgeDays`. Then comes dedup: the url_key or fingerprint is in `seen_keys`, or in keys from the home's existing Properties (`url_key(listingUrl)` and `fingerprint(type, price, landSize, builtSize, address)`), or already in this batch. What remains is truncated to `maxResultsPerRun`. It inserts the suggestions, calls `add_seen`, and updates the run (`succeeded`, counts, sites, usage) and the search's `lastRun*`. It then calls `send_digest_if_any(home_id, search, run, new_items)` from Task 5 (until Task 5 exists, stub it as a no-op inside this module). Returns `{received, new, duplicates}`. 404 for an unknown run, 409 if the run is not `running`.
- `fail_run(run_id, body: RunnerFail)` with `RunnerFail(reason: Literal["usage_limit","error"], message: str = "", usage: SearchUsage | None = None)`. It sets the run status `usage_limited` or `failed` and updates `lastRun*`. A failure email (Task 5) is sent only for `error`, or for the 3rd `usage_limited` on that slot.
- Routes: `POST /api/property-search/runner/claim` returns 200 with the claim or 204. `POST /api/property-search/runner/runs/{run_id}/complete` and `.../fail`. All require role ≥ `normal` (`require_auth("normal")`).

- [ ] **Step 1: Failing tests** (create a daily search with `runRequestedAt` set via the run-now route):
  - `test_claim_returns_due_search_and_204_when_none`.
  - `test_claim_twice_returns_204_second_time`.
  - `test_stale_running_run_is_reclaimed`: insert a running run with `startedAt` 3 h ago, then claim succeeds.
  - `test_complete_stores_new_and_counts_duplicates`: complete with 2 listings, then claim again via run-now and complete with the same 2 plus 1 new, giving `new == 1, duplicates == 2`.
  - `test_complete_dedups_within_batch`.
  - `test_complete_skips_malformed_listings`: `[{"title":"x"}, {"title":"ok","listingUrl":"https://a.si/1","price":"abc"}, valid]` gives `new == 1`, status 200.
  - `test_complete_drops_too_old_listings`.
  - `test_complete_respects_max_results`.
  - `test_complete_skips_existing_property_by_fingerprint`.
  - `test_fail_usage_limit_leaves_search_due`.
  - `test_ro_token_cannot_claim`: create an API token with role `ro` via `/api/auth/tokens` and use `Authorization: Bearer` on a fresh `TestClient` → 403.
- [ ] **Step 2:** Run. Expect FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expect PASS.
- [ ] **Step 5:** Commit: `feat(property-search): runner claim/complete/fail API`.

### Task 5: Brevo email

**Files:**
- Create: `property_search_email.py`. Modify: `property_search_ingest.py` (replace the stub), `routes/property_search.py` (test-email).
- Test: `tests/test_property_search_email.py`

**Interfaces — Produces:**
- `render_digest(search: PropertySearch, run: PropertySearchRun, items: list[PropertySuggestion], app_base_url: str) -> tuple[str, str, str]` returns `(subject, html, text)`. The subject is `f"{len(items)} new propert{'y' if len(items)==1 else 'ies'} — {search.name}"`. The body has one block per item (title linked to `listingUrl`, price with currency, land/built m², location, sourceSite, reason). Then, if a base URL is set, a link to `{app_base_url.rstrip('/')}/#/properties`. Then "Sites queried:" followed by the sorted distinct hosts of `run.sites`, and "Usage:" with `totalTokens` plus per-model lines and each quota as `"{label}: {usedPct}% used"` (`"n/a"` when None). All user and AI text is HTML-escaped.
- `render_failure(search, run) -> tuple[str, str, str]`: subject `f"Property search failed — {search.name}"`.
- `async send_brevo(cfg: PropertySearchConfig, subject: str, html: str, text: str) -> None`: `POST https://api.brevo.com/v3/smtp/email`, headers `api-key` and `accept: application/json`, JSON `{sender:{email,name}, to:[{email} for recipients], subject, htmlContent, textContent}`, timeout 20 s. Raises `EmailError(msg)` on a non-2xx response (including Brevo's `message`) or when the key, sender or recipients are missing.
- `send_digest_if_any(home_id, search, run, items)` / `send_failure(home_id, search, run)`: synchronous wrappers. They do nothing if `items` is empty or the config is incomplete. They catch `EmailError`/`httpx.HTTPError`, store `emailError` on the run, and never raise. Runner routes are sync `def`, so the wrappers call the async function via `anyio.from_thread.run` or simply use a sync `httpx.Client` (implementer's choice; one HTTP code path).

- [ ] **Step 1: Failing tests** (respx mocks `https://api.brevo.com/v3/smtp/email`):
  - `test_digest_contains_sites_and_usage`: hosts `nepremicnine.net` and `bolha.com` appear, plus `Weekly: 34% used` and `5-hour: n/a`.
  - `test_digest_escapes_html`: a title `<script>` is escaped.
  - `test_send_brevo_posts_expected_payload`: assert the header and the recipient list.
  - `test_send_brevo_raises_on_401`.
  - `test_complete_survives_brevo_failure`: Brevo returns 500, the complete route still returns 200, the run is `succeeded`, and `GET runs` shows an `emailError`.
  - `test_no_email_when_zero_new`: respx route not called.
  - `test_test_email_endpoint_502_on_brevo_error`.
- [ ] **Step 2:** Run. Expect FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expect PASS.
- [ ] **Step 5:** Commit: `feat(property-search): Brevo digest and failure emails`.

### Task 6: Retention cleanup and reset

**Files:**
- Create: `property_search_cleanup.py`. Modify: `main.py` (`_lifespan`: start and cancel `property_search_cleanup_loop()`), `persistence_properties.py` (`reset_properties` calls `reset_property_search`).
- Test: `tests/test_property_search_cleanup.py`

**Interfaces — Produces:** `cleanup_home(home_id: str, now: datetime) -> int` deletes the `new` and `rejected` suggestions with `createdAt < now - retentionDays`, plus the runs older than 90 days. It returns the number of suggestions deleted. It never deletes `pinned`/`accepted` or `property_seen`. `property_search_cleanup_loop()` sleeps 60 s per iteration and runs `cleanup_home` for every home at most once per local date (track the last date in a module-level variable), logging exceptions like `backup_scheduler`.

- [ ] **Step 1: Failing tests:** `test_cleanup_deletes_old_new_and_rejected`, `test_cleanup_keeps_pinned_and_accepted`, `test_cleanup_keeps_seen_so_no_resuggest` (after cleanup, a complete with the same URL counts as a duplicate), `test_reset_properties_clears_suggestions`.
- [ ] **Step 2:** Run. Expect FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expect PASS. Then run the full backend suite with `python -m pytest -q` (expect everything green).
- [ ] **Step 5:** Commit: `feat(property-search): retention cleanup loop`.

### Task 7: Frontend store

**Files:**
- Create: `packages/editor/src/lib/propertySearchStore.svelte.ts`
- Test: `packages/editor/test/propertySearchStore.test.ts`

**Interfaces — Produces:** `createPropertySearchStore(getHomeId: () => string | null)` returns a reactive object `{ searches, suggestions, loaded, loadError, newCount, init(), createSearch(data), updateSearch(id, patch), deleteSearch(id), runNow(id), listRuns(id), accept(id), reject(id), togglePin(id), loadConfig(), saveConfig(patch), sendTestEmail() }`, following `propertiesStore.svelte.ts`'s fetch/error style. `newCount` is derived as the count of suggestions with `status === "new"`. `accept` returns the created `Property` and the caller re-inits `propertiesStore`. TS types mirror the Task 1 models.

- [ ] **Step 1: Failing tests** (mock `fetch` like `propertiesStore.test.ts`): `init loads searches and suggestions`, `newCount counts only new`, `accept removes suggestion locally`, `saveConfig sends PUT`.
- [ ] **Step 2:** Run `npx vitest run test/propertySearchStore.test.ts`. Expect FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expect PASS.
- [ ] **Step 5:** Commit: `feat(property-search): frontend store`.

### Task 8: Suggestions tab and searches modal

**Files:**
- Create: `components/PropertySuggestionsTab.svelte`, `components/PropertySearchesModal.svelte`
- Modify: `components/PropertiesPage.svelte` (add `Tabs` `[{id:"list"}, {id:"suggestions", label: "Suggestions (N)" when N>0}]`, following the ChoresPage pattern, and a new prop `searchStore`), the parent that creates the stores, `locales/en.json`, `locales/fr.json`
- Test: `test/PropertySuggestionsTab.test.ts`, `test/PropertySearchesModal.test.ts`, update `test/PropertiesPage.test.ts`

**Behaviour:**
- **Suggestions tab:** a toolbar with a FilterButton (filter by search) and a "Searches" Button that opens the modal. The list is a Card per suggestion: image when available (`loading="lazy"`, hidden on error), title (link to the listing, `target="_blank" rel="noopener noreferrer"`), type, price, sizes, location, source site, published date, the reason, and a "📌" marker when pinned. Actions: Accept / Pin-Unpin / Reject (icon Buttons with titles). The empty state reads "No suggestions yet" and, when no search exists, points to the Searches button. A last-run line per search shows the time, status, counts and the error.
- **Searches modal:** a list of searches (name, schedule summary, enabled toggle, Run now, edit, delete with confirmation), plus a create/edit form: name, prompt (textarea, 6 rows, placeholder with the Novo Mesto example), frequency select, time input, day-of-week select (weekly), day-of-month number (monthly), max per run, max listing age (days). "Run now" shows a toast or inline note: "Queued, it will run at the runner's next check (≤ 15 min)".
- Follow [Svelte 5 + jsdom event delegation]: mount on `document.body` and dispatch with `bubbles:true`.

- [ ] **Step 1: Failing tests:** `renders suggestions with reason and link`, `accept calls store.accept and refreshes properties`, `filter by search hides others`, `searches modal creates a search with entered prompt`, `weekly shows day-of-week select`, `PropertiesPage shows suggestions badge count`.
- [ ] **Step 2:** Run. Expect FAIL.
- [ ] **Step 3:** Implement, with the EN and FR strings.
- [ ] **Step 4:** Run `npx vitest run` (full suite). Expect PASS. Run `npx svelte-check` with no new errors.
- [ ] **Step 5:** Commit: `feat(property-search): suggestions inbox and searches UI`.

### Task 9: Settings panel

**Files:**
- Create: `components/settings/SettingsPropertySearch.svelte`. Modify: `SettingsPage.svelte` (group `{ id: "propertySearch", icon: "🔎", adminOnly: true }`), locales (`settings.nav.propertySearch` + `propertySearch.settings.*`).
- Test: `test/SettingsPropertySearch.test.ts`

**Behaviour:** fields for retention days, Brevo API key (password input; placeholder "•••• set" when `brevoApiKeySet`, an empty value keeps the key), sender email and name, recipients (comma or newline separated textarea, split and trimmed), and myhome base URL for email links. Save and "Send test email" buttons, with an inline result. A help block "Connect the runner" explains: expose port 8000 in the add-on, create an API token (role normal) in Settings → Security, and put `MYHOME_URL` and `MYHOME_TOKEN` in the runner's `config/settings.env`. It links to `https://github.com/floco/property-search-runner`.

- [ ] **Step 1: Failing tests:** `loads config and shows key-set placeholder`, `save sends recipients as array`, `empty key field not sent as a new key`, `test email shows error message`.
- [ ] **Step 2:** Run. Expect FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full vitest suite. Expect PASS.
- [ ] **Step 5:** Commit: `feat(property-search): settings panel`.

### Task 10: Runner repo

**Files** (in `/projects/property-search-runner`, `git init`):
- `propertysearch/agent.py`: copy jobsearch's `agent.py` (`gh api repos/floco/jobsearch/contents/jobsearch/agent.py`) and keep `run_claude`, `_read_stream`, `_usage`, `UsageLimitError`, `AgentError`, `ClaudeRun`, `RunUsage` unchanged. Replace `build_prompt` with `build_prompt(template: str, claim: dict) -> str` (placeholders `{today}`, `{max_results}`, `{max_age_days}`, `{criteria}`, `{seen_list}`, user blocks substituted last, as jobsearch does). Add `parse_listings(result: str) -> tuple[list[dict], list[str]]`, which extracts the last JSON object `{"listings":[...], "sitesQueried":[...]}` from the answer. Items missing `title`/`listingUrl`/`reason` are dropped.
- `propertysearch/api.py`: `class MyHome(base_url, token)` with `claim() -> dict | None`, `complete(run_id, payload)`, `fail(run_id, reason, message, usage)`, using httpx with a 30 s timeout and Bearer auth.
- `propertysearch/usage.py`: `to_search_usage(u: RunUsage) -> dict` gives `{"provider":"claude-code", tokensByModel, totalTokens, quotas:[{"label":"Weekly","usedPct":weekly_pct},{"label":"5-hour","usedPct":five_hour_pct}]}`.
- `propertysearch/main.py`: `main(argv)` takes the `--check` (GET `/api/auth/me` with the token and print the user and role), `--dry-run "<prompt>"` (run Claude with a fake claim and print JSON) and default modes. The default loop is: claim → build prompt → `run_claude` → `complete(listings, sitesQueried = parsed sites ∪ hosts of ClaudeRun.pages, searchQueries = ClaudeRun.searches, usage)`. It sends `fail("usage_limit")` on `UsageLimitError` and stops the loop (no point continuing). It sends `fail("error")` on `AgentError`/parse failure and continues to the next claim. It keeps going until `claim()` returns None.
- `propertysearch/config.py`: reads `config/settings.env` (`MYHOME_URL`, `MYHOME_TOKEN`, `CLAUDE_BIN` default `/root/.local/bin/claude`, `TIMEOUT_S` default 1500).
- `agent_prompt.md`: the instructions from the spec's runner section. It must tell Claude to find the right local portals for the country/type in the criteria itself, keep only listings published on or after `today - max_age_days`, skip the seen list, rank by fit, return at most `{max_results}`, and end the answer with exactly one JSON object `{"listings":[{title,type,price,currency,landSize,builtSize,bedrooms,bathrooms,location,sourceSite,listingUrl,imageUrl,publishedAt,reason}], "sitesQueried":[urls]}`, with `type` among `land|house|new_build` and numbers as numbers.
- `run.sh`: `flock -n /tmp/property-search-runner.lock python3 -m propertysearch.main >> logs/$(date +%F).log 2>&1`, and delete logs older than 60 days.
- `README.md` (setup, config, cron line, commands), `config/settings.env.example`, `.gitignore` (`config/settings.env`, `logs/`), `requirements.txt` (`httpx`), `tests/`.
- Tests: `test_build_prompt_substitutes_and_protects_braces`, `test_parse_listings_takes_last_json_and_drops_incomplete`, `test_to_search_usage_maps_windows`, `test_main_loop_completes_then_stops_on_204` (fake `MyHome` and a fake `run_claude`), `test_main_usage_limit_reports_and_stops`, `test_main_error_reports_and_continues`, and `test_read_stream_*` copied from jobsearch's tests.

- [ ] **Step 1:** Write the failing tests and run `python3 -m pytest -q`. Expect FAIL.
- [ ] **Step 2:** Implement. Run the tests. Expect PASS.
- [ ] **Step 3:** Commit: `feat: property search runner`.

### Task 11: Ship, deploy and end-to-end

- [ ] **Step 1:** In myhome, run the full backend and frontend suites (both green), add an `addon/CHANGELOG.md` entry under an "Unreleased" heading if the CI gate requires it (check `.github/workflows`), push the branch, and open a PR.
- [ ] **Step 2:** Run `gh repo create floco/property-search-runner --public --source /projects/property-search-runner --push`.
- [ ] **Step 3:** Start an isolated myhome instance from the branch (see the demo-home memory's isolated-instance recipe; restart uvicorn after edits per the dev-server memory). Create an admin API token with role normal, write `config/settings.env` (chmod 600), and run `python3 -m propertysearch.main --check`. Expect it to print the user and role.
- [ ] **Step 4: Live e2e (1 run of the user's quota).** In the UI, create a search with the user's example prompt ("terrains d'au moins 800 m² en Slovénie autour de Novo Mesto à moins de 200 000 €"), daily, max 5, age 30. Configure Brevo if the user gives a key and recipients (ask; otherwise skip the email and say so). Click Run now and run `./run.sh` once. Verify: suggestions appear in the tab with real listing URLs, the run shows sites and usage with the weekly %, and the email arrives if configured. Accept one and check it appears in Properties. Run now plus `./run.sh` a second time is allowed only if needed to check dedup.
- [ ] **Step 5:** Install the cron line `*/15 * * * * /projects/property-search-runner/run.sh` in the root crontab (`crontab -l` first, then append, never replace). Point it at the real add-on URL only once the user provides it. Until then, leave the entry commented out with a note in the README.
- [ ] **Step 6:** Report to the user: PR link, runner repo link, e2e results (what was found, the usage %), and what still needs their input (add-on URL/token, Brevo key, recipients).
