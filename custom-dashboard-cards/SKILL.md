---
name: custom-dashboard-cards
description: Build a polished Home Assistant dashboard from hand-written custom Lovelace cards. One JavaScript file holds all the cards, a JS config module describes the dashboards, a deploy script pushes them over the WebSocket API, a local preview harness renders the cards with mock states, and headless-Chrome checks confirm the result. Use when someone wants a custom or beautiful dashboard, custom cards, or a repeatable way to edit and deploy dashboards with Claude.
---

# Custom dashboard cards

## Project layout

```
home-dash/
  home-dash.js      all custom cards (one file, registered as one Lovelace resource)
  dashboard.mjs     exports the dashboard configs (views, sections, card options) as plain JS objects
  deploy.mjs        HA_TOKEN=... CARD_V=N node deploy.mjs  → creates helpers and dashboards, saves the configs
  preview/          index.html + states.json (+ ws_*.json mocks) for local rendering
  staged/           numbered copies of home-dash.js for every version (for exact rollbacks)
  backups/          originals of anything you replaced (old dashboards, energy prefs)
```
The template `templates/deploy.mjs` is a starting point.

## Card framework (inside home-dash.js)

- **A base class** (`HomeCardBase extends HTMLElement`) with:
  - `setConfig(config)` that merges `static defaults`,
  - a `hass` setter that re-renders only when an entity from `watched()` changed,
  - and helpers: `st(id)` (state object), `num(id)`, `isOn(id)`, `call(domain, service, data)`,
    `toggleLights(ids)` and `bindMoreInfo()` (for `[data-more-info]` elements).
- **Render into the shadow root:** each card renders by setting `shadowRoot.innerHTML`. Escape every string
  from states with an `esc()` helper.
- **Timed updates:** cards that show times ("5 min ago", the current rate period) re-render on a 60 s timer.
- **Shared design tokens:** one colours object (navy card, teal = good, amber = attention, red = problem,
  muted text) and a shared CSS string, so every card matches.
- **Registration:** add each card to `customElements` and to `window.customCards`, so it appears in the card
  picker. Print a version banner to the console.
- **History in cards:** call `hass.callWS({type: 'history/history_during_period', ...})` on load and every
  ~10 min. Don't fetch on every state change.

## Dashboards as code

- **Write the configs in `dashboard.mjs`:** sections view (`type: 'sections'`, `max_columns`), plus panel
  views for big cards.
- **Keep the house facts in config,** not code: lights per area, the plant list, the network wiring.
- **Deploy over WebSocket:** `lovelace/dashboards/create` (once), then `lovelace/config/save`.
- **Back up first:** before replacing an existing dashboard, save its config to `backups/`.
- **Admin-only views:** use `require_admin: true` on dashboards with risky controls.

## Cache-busting

- **The resource URL carries the version:** `/local/home-dash.js?v=N`. Copy the file to `/config/www/`
  (scp over the SSH add-on), then update the resource URL with the next `N`. Without the bump, phones keep
  the old file.
- **Card version:** bump `CARD_VERSION` too, and say which version is live when you report back.

## Preview locally before deploying

- **The harness:** `preview/index.html` loads `home-dash.js`, builds a fake `hass` from `states.json`, and
  renders a chosen dashboard or view.
- **URL parameters** control it: `?dash=&view=&on=<entity,...>&sun=above_horizon|below_horizon&elev=&t=HH:MM&w=<px>`.
  - Use them to try day and night, golden hour, lights on or off, and a phone or desktop width.
- **Serve it:** `python3 -m http.server 8765`. Screenshot with headless Chrome (`--screenshot`), then **look at
  the screenshot** before deploying.

## After deploying, verify

- **Check the live page:** run `ha-screenshot.mjs` (from `home-assistant-foundations`) against the live URL.
  It must report **no error cards**.
- **Report honestly:** say what's live, what you checked, and anything you couldn't check (e.g. a tap that would
  switch the owner's real lights).

## Iterating with the owner (lessons learned)

- **Change only what they point at.** Don't "improve" nearby things in the same pass. Unrequested extras are
  the most common reason feedback turns into "this is worse".
- **Save every version:** `staged/home-dash.vX.Y.Z.js`. Mark the ones they approve (`-GOOD`). "Go back N
  versions" then means restoring the exact file. Re-number on the way out: restore it as the next version,
  never reuse an old number.
- **When a request is ambiguous** ("make the window less tall from the top"), ask one multiple-choice
  question with a small ASCII sketch of each option, rather than guessing.
- **When a tap "does nothing,"** check the entity states first. An integration outage looks exactly like a
  broken card.
