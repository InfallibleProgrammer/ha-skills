---
name: home-assistant-foundations
description: Set up and safely operate a Home Assistant OS install. Covers installing it on a Raspberry Pi or mini PC, getting API, WebSocket and SSH access from a laptop, backups, safe updates and rollbacks, and helper scripts for talking to Home Assistant. Use when someone is starting a Home Assistant setup, needs Claude to reach their Home Assistant, or is about to update or restart it.
---

# Home Assistant foundations

The groundwork every other home skill relies on: a reachable Home Assistant, a way for Claude to talk to it,
and habits that keep the owner's home working while you change things.

## 1. Install (if they don't have Home Assistant yet)

Ask what hardware they have. Recommend Home Assistant **OS** (not Container or Core), because add-ons such as
SSH, Tailscale and Let's Encrypt need it.

- **Raspberry Pi (4 or 5):** use an NVMe drive or SSD rather than an SD card, since SD cards wear out from the
  database. Flash "Home Assistant OS" with Raspberry Pi Imager.
- **Mini PC (Intel N100 or similar):** follow the "Generic x86-64" install guide.
- **Network:** plug it into the router or switch with Ethernet. Then reserve its IP address in the router
  (a DHCP reservation), so the address never changes.
- **First visit:** open `http://homeassistant.local:8123`, or `http://<HA_IP>:8123` if that doesn't load,
  then create the owner account and set the home location, time zone and units.

## 2. Give Claude access

Ask the owner to do each step themselves. Never ask for their password.

1. **Long-lived access token:** Profile (bottom left) → Security → Long-lived access tokens → Create.
   - Have them set it as an environment variable (`export HA_TOKEN=...`) or paste it once into the session.
   - Explain that this token can do anything the account can, including unlocking doors. Suggest deleting it
     when the work is done and making a new one later.
2. **SSH add-on:** Settings → Add-ons → Add-on store → "Advanced SSH & Web Terminal" (community add-on).
   - Set an `authorized_keys` entry using their public key, choose a port (e.g. 2222), and turn protection
     mode off only if it's really needed.
   - It gives you the `ha` command (`ha core info`, `ha core logs`, `ha host logs`, `ha network info`,
     `ha apps ...`).
   - On recent versions, `ha apps` replaces the old `ha addons`.
3. **Check the connection:**
   ```bash
   curl -s -H "Authorization: Bearer $HA_TOKEN" http://<HA_IP>:8123/api/config
   ```
4. **MCP server (optional):** if their Claude client supports MCP, Home Assistant's "Model Context Protocol
   Server" integration exposes `http://<HA_IP>:8123/api/mcp`.

## 3. Ways to talk to Home Assistant

| Need | Use |
|------|-----|
| Read states, call services | REST: `GET /api/states/<entity_id>`, `POST /api/services/<domain>/<service>` |
| Change configuration: dashboards, helpers, entity registry, integration options | WebSocket API. See `scripts/ha-ws.mjs` |
| Logs, network, updates, add-ons | SSH plus the `ha` command |
| Check what a dashboard really looks like | `scripts/ha-screenshot.mjs`: headless Chrome, logged in with the token, lists error cards |

Useful WebSocket message types:
- **Entity registry:** `config/entity_registry/list` and `config/entity_registry/update`. Updates can enable or
  disable an entity, rename it, or set `new_entity_id`.
- **Dashboards:** `lovelace/dashboards/list`, `lovelace/dashboards/create`, `lovelace/config/save`, and
  `lovelace/resources` with its `create` and `update` messages.
- **Helpers:** `input_boolean/create`, `input_datetime/create`, `timer/create`, and so on.
- **History:** `history/history_during_period`.

**History gotcha:** REST `/api/history/period/<start>` returns only **one day** unless you also pass
`end_time=`. If your history "stops" early, you forgot `end_time`.

**Integration options** (for example UniFi) are a flow: `POST /api/config/config_entries/options/flow` with
`{"handler": "<entry_id>"}`, then `POST .../flow/<flow_id>` with the full form.
- Collapsible sections arrive as an `expandable` field. Submit them as nested objects.
- Always resend every existing value. Anything you leave out gets reset.

## 4. Backups and updates

- **Before any risky change,** take a backup: `ha backups new --name "before <change>"`, or Settings → System →
  Backups.
- **Updating core:** `ha core update --version <x.y.z> --backup`. Only update when you have a reason, then check
  the integrations afterwards.
  - Watch for regressions: an integration stuck in `setup_retry`, or every device from one brand going
    "unavailable".
  - Real example: one Home Assistant patch release changed the Python version and broke a lighting
    integration's secure connection ("check_hostname requires server_hostname"). The next patch fixed it.
  - **The fix pattern:** search the error text together with the version, then either update to the next
    patch or roll back with `ha core update --version <previous>`.
- **Restarts:** some config (for example http settings) restarts Home Assistant automatically. Warn the owner
  that it'll be offline for a minute or two, and wait for `/api/config` to report `"state":"RUNNING"`.

## 5. Configuration notes for recent releases

- **http settings** (`use_x_forwarded_for`, `trusted_proxies`, SSL) moved from `configuration.yaml` to the UI
  (Settings → System → Network).
  - A leftover `http:` block in YAML is ignored and raises a repair notice.
  - Over the API, `http/config/configure` applies the change in trial mode (Home Assistant restarts and reverts
    by itself unless confirmed), and then `http/config/promote` makes it permanent.
- **Editing YAML over SSH:** keep a dated copy first (`cp configuration.yaml configuration.yaml.bak-YYYYMMDD`),
  then check the config before restarting.

## 6. Working habits with the owner

- **Ask first** before deleting anything, turning off network ports or Wi-Fi, changing remote access, or
  updating or rolling back Home Assistant.
- **Keep secrets out of files:** never write tokens, passwords or API keys into files, dashboards or scripts.
  Read them from environment variables, and let the owner type passwords into the Home Assistant UI.
- **One change, preview, deploy, confirm.** Keep a numbered copy of every version of anything you're iterating
  on, such as dashboard JS or YAML, so "go back 2 versions" is exact.
- **Report honestly:** "deployed, page loads with no error cards" is something you can check. "Looks right" is
  for the owner to judge from a screenshot.
- **Keep a to-do file** for ideas you put off, for example local HTTPS, two-factor login and phone alerts.

## Scripts

- `scripts/ha-ws.mjs`: sends one or more WebSocket messages and prints the results. Uses Node 22+ (built-in
  WebSocket) with `HA_HOST` and `HA_TOKEN` env vars. For many messages, pass them NUL-separated through
  `xargs -0`.
- `scripts/ha-screenshot.mjs`: logs into a dashboard in headless Chrome using the token, prints any error cards
  and console errors, and saves a screenshot.
