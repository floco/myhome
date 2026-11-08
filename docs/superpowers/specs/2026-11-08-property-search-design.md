# AI Property Search (Properties module) + external runner

Date: 2026-11-08

## Intent

The user wants the Properties module to go looking for new land and houses by itself. The user writes
a search in plain words, for example *"plots of at least 800 m² in Slovenia around Novo Mesto, under
€200,000"*. On a schedule, an AI works out which listing sites suit that search, queries them, and
keeps the best new matches. The matches land in a **Suggestions inbox** in myhome for the user to
triage, and a summary email goes out through Brevo.

The AI has to run on a **Claude Pro/Max subscription, not an API key**. That means using Claude Code
in headless mode. The user does **not** want myhome itself tied to any AI provider. So the work
splits in two:

1. **myhome (this repo):** everything that doesn't depend on a provider. That covers search
   definitions, schedule, storage, de-duplication, retention, flagging, the email digest and the UI.
   myhome exposes a small, generic "runner API".
2. **`property-search-runner` (new repo, `floco/property-search-runner`, cloned at
   `/projects/property-search-runner` on this server, where Claude Pro is already logged in):** a
   thin worker modelled on `floco/jobsearch`. It polls myhome for due searches, runs headless Claude
   Code with WebSearch/WebFetch, and posts results back. It is the only Claude-specific piece. A future
   OpenAI/Ollama runner could implement the same API without changing myhome.

## Goals

- Several named searches per home, each with its own free-text prompt and parameters.
- Each search's schedule is set in myhome (daily / weekly / monthly at a time). The runner only executes.
- The same property is never suggested twice, whichever search or site it comes from, and even after
  it was rejected or cleaned up.
- Suggestions are stored in the DB and triaged in the UI (accept → becomes a normal Property, reject,
  pin to keep).
- A retention period auto-deletes old untriaged suggestions. Pinned ones are kept.
- After each run with new suggestions, a Brevo email goes to one shared recipient list. It lists the
  new suggestions, the sites queried, the tokens used and the remaining Claude plan usage.

## Non-goals

- No AI provider SDK, CLI or API key inside myhome or the HA add-on.
- No scraping code in myhome. Finding listings is entirely the runner's job.
- No MCP tools for this feature (could come later).
- No price-change or listing-removed tracking on suggestions (could come later).
- No per-search recipient lists. The list is shared by all searches.

## Anti-goals (would make it a failure even if it "works")

- A property the user already saw (suggested, accepted, rejected, or already tracked in Properties)
  shows up again.
- myhome's code or data model mentions Claude by name beyond a free-text `provider` label coming from
  the runner.
- The runner hammers the subscription: a search runs more often than its schedule, or two runners
  execute the same search concurrently.
- Secrets (Brevo key, runner token) leak to non-admin users or into logs/emails.

## Constraints and existing pieces to reuse

- Properties is a SQL-table module (`schema.py`, `persistence_properties.py`, `models_properties.py`,
  `routes/properties.py`). New tables follow the same pattern and are **home-scoped** (see
  [category-table home-scoping lesson]: every fixed-id/seeded table needs a per-home key).
- `Property` already has `type` (land/house/new_build), `price`, `landSize`, `builtSize`, `bedrooms`,
  `bathrooms`, `address`, `listingUrl`, `notes`, `pros`, `cons`, `status` (default `watching`).
- Scheduling: reuse the shape of `backup_scheduler.py` (`frequency` daily/weekly/monthly + `time` +
  `dayOfWeek` + `dayOfMonth`, `_should_run_today`). Background loops are started in `main.py`'s
  `_lifespan`.
- Auth: myhome already has role-scoped **API tokens** (`models_auth.ApiToken`, Bearer auth in
  `deps.py`). The runner uses a normal API token created in Settings, so no new token mechanism is
  needed. The token needs role `normal` or higher on the homes it serves.
- Network: the add-on already exposes optional port `8000/tcp` for direct (non-ingress) API access
  (used by MCP clients). The runner uses that base URL.
- Frontend: Svelte 5 + svelte-i18n. Every new string goes in **EN and FR**. Use the shared UI
  components (Modal, Button, Input, Card, Tabs, StatTile, DatePicker, FilterButton).
- Settings is sidebar-navigated with panel components (`packages/editor/src/lib/components/settings/`).

## Data model (myhome)

### `property_searches` (per home)
| field | notes |
|---|---|
| id, homeId | |
| name | e.g. "Terrains Novo Mesto" |
| prompt | free text, the user's criteria |
| enabled | bool |
| frequency | `daily` \| `weekly` \| `monthly` |
| time | `HH:MM` in the add-on's local timezone (`TZ` env, which HA sets for add-ons; fall back to UTC). Backups stay unchanged (they use UTC). |
| dayOfWeek / dayOfMonth | as in backups |
| maxResultsPerRun | int, default 10. **Decided:** "max per day" means **per run**, i.e. at most N suggestions per email. |
| maxListingAgeDays | int, default 7: only listings published within this many days |
| runRequestedAt | nullable, set by "Run now" |
| lastRunAt, lastRunStatus, lastRunError | for display |

### `property_suggestions` (per home)
`id, homeId, searchId, runId, title, type (land/house/new_build/null), price, currency, landSize,
builtSize, bedrooms, bathrooms, location (free text), sourceSite, listingUrl, imageUrl, publishedAt,
reason (why it matches), status (new|pinned|accepted|rejected), createdAt, acceptedPropertyId`.

### `property_seen` (per home): the never-again ledger
`homeId, urlKey, fingerprint, firstSeenAt`. One row per suggestion ever stored. **Never deleted by
retention**, so rejected or cleaned-up properties never come back.

### `property_search_runs` (per home)
`id, homeId, searchId, startedAt, finishedAt, status (running|succeeded|failed|usage_limited),
error, sites (json list), searches (json list of queries), usage (json), receivedCount, newCount,
duplicateCount`. Kept 90 days (builder's call on the exact number).

### Module settings (per home, in the existing settings document)
`propertySearch: { retentionDays (default 30), brevoApiKey, senderEmail, senderName, recipients: [] }`.
The Brevo key is write-only from the UI (masked on read, admin-only to change).

## De-duplication

- **urlKey:** normalised listing URL (lowercase host, strip `www.`, fragment, tracking params such as
  `utm_*`/`fbclid`/`gclid`, trailing slash).
- **fingerprint:** a coarse cross-site key built from type + rounded price + rounded land/built size
  + normalised location. *Builder's call on the exact rounding.* It must catch the same plot listed on
  two agency sites. A false-positive merge (dropping a genuinely different property) is acceptable to
  the user's goal: "never twice" matters more than "never miss one".
- On ingest, a listing is a duplicate if its urlKey **or** fingerprint is in `property_seen`, **or**
  it matches an existing `Property` in that home by URL key **or** by the same fingerprint (computed on the
  fly from type, price, sizes and `address`). No backfill migration is needed. Duplicates are counted, not stored.
- If the key fingerprint fields (price and at least one size) are missing, no fingerprint is used, so a
  sparse listing can't collide with everything.
- Ingest also drops listings whose `publishedAt` is older than `maxListingAgeDays` (when provided),
  then keeps at most `maxResultsPerRun` (in the order the runner ranked them).
- To save tokens, the runner gets a "recently seen" list (last ~300 urls/titles) to include in its
  prompt. myhome's ingest check is the real guarantee.

## Runner API (generic, Bearer API token)

All under `/api/property-search/runner/`. Provider-neutral naming.

- `POST /claim`: returns the next **due** search across all homes the token can access, or 204.
  Atomically creates a `running` run row so a second poll can't claim it. A `running` run older than
  2 h is treated as dead (marked failed) and the search becomes claimable again.
  Response: `{runId, homeId, searchId, name, prompt, maxResultsPerRun, maxListingAgeDays, today,
  seen: [{url, title}]}`.
- `POST /runs/{runId}/complete`: body
  `{listings: [...suggestion fields...], sitesQueried: [str], searchQueries: [str],
  usage: {provider: str, tokensByModel: {model: int}, totalTokens: int,
  quotas: [{label: str, usedPct: int|null}]}}`.
  myhome de-dups, stores, records the run, sends the email (if there's at least one new suggestion)
  and returns counts.
- `POST /runs/{runId}/fail`: body `{reason: "usage_limit"|"error", message, usage?}`.
  `usage_limit` leaves the search due, so it's retried on a later poll. Plain `error` marks the run
  failed and the search waits for its next slot.

"Due" means: enabled and (`runRequestedAt` is set, or the schedule slot for today has passed and
there's no succeeded run for it yet). Usage-limited retries are capped at 3 per slot (builder's call).

## myhome UI

- **Properties page → new "Suggestions" tab**, with a badge counting `new` suggestions.
  - The list/cards show: image, title, type, price, sizes, location, source site, published date,
    the AI's reason, and a link to the listing. A filter picks the search (FilterButton pattern).
  - Actions: **Accept** (creates a `Property` in status `watching`, pre-filled with name=title, type,
    price, sizes, bedrooms, bathrooms, address=location, listingUrl, notes=reason + source; the
    suggestion becomes `accepted` and leaves the inbox), **Reject**, **Pin / Unpin**.
  - A small "last run" line per search (time, status, new/duplicate counts, error if any).
- **Searches management:** a "Searches" sub-view in the Suggestions tab (or a modal from it) to
  create/edit/delete/pause searches: name, prompt (multiline), frequency + time/day, max per run,
  max listing age. Plus a **Run now** button. *Builder's call on whether this lives in the tab or in
  Settings. The tab is preferred so it stays next to its results.*
- **Settings → Properties panel (or Integrations):** retention days, Brevo API key (masked), sender,
  recipients list, a **Send test email** button, and a short "how to connect the runner" help text
  (base URL + create an API token).
- Everything in EN and FR.

## Background jobs (myhome)

- **Retention cleanup:** a daily loop in `_lifespan`, same pattern as the backup/digest loops.
  It deletes suggestions with status `new` older than `retentionDays`, and rejected suggestions'
  details older than `retentionDays`. It never touches `pinned`, `accepted` or `property_seen`. It
  prunes run history past its own horizon.
- No scheduler loop is needed for searches: "due" is evaluated lazily on `/claim`.

## Email (sent by myhome via Brevo)

Brevo transactional API (`POST https://api.brevo.com/v3/smtp/email`, `api-key` header), HTML and
text parts, to the shared recipient list. Sent after a run completes with ≥1 new suggestion. *(Call:
no email for zero new results.)* Subject: `"<N> new properties — <search name>"`.

Body:
- each new suggestion: title, price, sizes, location, source site, reason, link to the listing;
- a link to the myhome Suggestions tab (the base URL is configurable in the settings above; it is
  optional, and the link is omitted if not set);
- **Sites queried:** the distinct hosts from `sitesQueried`;
- **Usage:** total tokens (with per-model breakdown) and each quota (e.g. "Weekly: 34% used,
  5-hour: 12% used"), rendered generically from `usage.quotas`.

Failures (`error` reason, or a usage limit after the last retry) send a short failure email to the
same recipients. *(Call: the user asked for no separate admin address.)* Language: the email uses
the home's UI language if one is stored, else English (builder's call).

## The runner (new repo `floco/property-search-runner`)

Modelled closely on `floco/jobsearch` (reuse its `agent.py` approach wholesale):

- Python 3, no web framework. A config file `config/settings.env` (chmod 600) holds `MYHOME_URL`,
  `MYHOME_TOKEN`, `CLAUDE_BIN`, and a timeout.
- Entry point `python3 -m propertysearch.main`: loops `claim` → run → `complete`/`fail` until `claim`
  returns 204. That way one cron tick drains all due searches, one at a time.
- Cron: every 15 minutes (`*/15 * * * *`), so "Run now" waits at most ~15 min. A lock file prevents
  overlapping ticks.
- Claude invocation: same flags as jobsearch (`-p --output-format stream-json --verbose
  --setting-sources project --tools WebSearch WebFetch --allowedTools WebSearch WebFetch
  --strict-mcp-config --no-session-persistence`), own process group, timeout kill.
- **Sites queried** = hosts of the WebFetch URLs plus the domains Claude reports using. **Usage** =
  `modelUsage` tokens from the `result` event, and `rate_limit_event.unifiedWindows.seven_day /
  five_hour` utilisation mapped to `quotas` labels "Weekly" / "5-hour". Usage-limit detection reuses
  jobsearch's markers and sends `fail(reason=usage_limit)`.
- `agent_prompt.md` template: tells Claude to work out the best listing sites for the country and
  property type in the user's criteria (local portals, agencies, classifieds), only keep listings
  published within `maxListingAgeDays` of `today`, skip anything in the seen list, rank by fit, return
  at most `maxResultsPerRun`, and output a strict JSON array with the suggestion fields plus
  `sitesQueried`. The runner validates the JSON (required: title, listingUrl, reason) and drops bad items.
- Tests with pytest, as in jobsearch (prompt building, stream parsing, usage mapping, API client with
  a fake server).
- `--dry-run` (claim nothing, run a given prompt, print JSON) and `--check` (verify the token and
  connectivity to myhome) commands.

## Decided by the user

- Architecture A: myhome holds data, settings and email; a separate, dedicated runner repo is the only
  Claude-specific part.
- Uses the Claude Pro subscription via Claude Code, not the API.
- Suggestions go to an inbox to triage, not straight into Properties.
- Several named searches, each with its own prompt and its own frequency/limits.
- One shared recipient list for all searches.
- Retention period for suggestions, cleanup process, and the ability to flag (pin) suggestions to
  keep them longer.
- The email shows the sites queried, the tokens used and the remaining Claude Pro usage.

## Calls made by Claude (user to confirm)

- Search times use the add-on's local timezone (`TZ`), and the runner's `today` is computed in that
  timezone too.
- Existing Properties are also matched by fingerprint, not only by URL.
- Emails are in English (the UI language lives only in the browser). Currency goes into `notes` on Accept.
- A missed weekly or monthly slot (myhome down, runner off) is caught up on the next claim.
- There is no per-home membership, so a runner token can reach every home.

- "Max per day" is interpreted as **max per run** (= per email).
- The never-again ledger (`property_seen`) is never cleaned up, even when suggestions are.
- No email when a run finds nothing new. A failure email goes to the shared recipients.
- Cross-site duplicates are caught by a coarse fingerprint. Occasional over-merging is accepted.
- The runner polls every 15 min, and myhome decides what's due.
- Searches are managed in the Suggestions tab. Global settings (retention, Brevo, recipients) are in
  Settings.

## Delivery scope (decided by the user)

- Create `floco/property-search-runner` as a **public** GitHub repo, cloned at
  `/projects/property-search-runner`.
- Install the `*/15` root cron entry for the runner on this server.
- One live end-to-end run against the user's Claude Pro plan is allowed (keep to 1–2 runs).
