---
name: troubleshooting-dropouts
description: Diagnose why devices keep going "unavailable" or "dropping off" in Home Assistant when the router or UniFi app says everything is fine. Pulls history over several days, measures each outage, groups simultaneous drops, separates integration and cloud blips from real network problems, checks logs and recent updates, and shows the results honestly on a dashboard. Use when someone reports devices dropping, unavailable entities, lights that won't respond, or flaky integrations.
---

# Troubleshooting dropouts

Most "dropouts" in Home Assistant are **the integration losing touch**, not the device leaving the network.
Prove which kind it is with data.

## 1. Pull history the right way

- **Several days, with an end time:** `GET /api/history/period/<start>?end_time=<now>&filter_entity_id=a,b,c&minimal_response&no_attributes&significant_changes_only=0`.
  Without `end_time` you only get one day.
- **For each entity, find each outage:** a run of `unavailable`, `unknown` or `not_home`. Record its **start
  time and how long it lasted**.

## 2. Read the pattern

| Pattern | Usually means |
|---------|---------------|
| Many integrations drop at the **same second** (every entity from one hub, e.g. all network entities, or all lights from one bridge) | That integration's connection to its hub blipped. The devices are fine. |
| One cloud device drops for 4–20 s on a near-regular rhythm (e.g. every ~50 min) | Cloud token or subscription refresh. Harmless. |
| One Wi-Fi device drops often, for longer | Weak Wi-Fi where it is, or an AP restarting. Check the AP's uptime and the device's signal strength. |
| A TV is unavailable for hours | Deep standby. Normal. |
| **Everything from one brand** goes unavailable and stays that way | The integration failed, often after a Home Assistant update. |
| Drops line up with an AP or switch restart | Check the gateway, AP and switch uptime sensors. A PoE-powered device restarts when its upstream port does. |

**Group the drops:** list the moments where two or more entities dropped within ~2 minutes of each other, then
see which integrations each group contains.

## 3. Rule out the Home Assistant host

- **Ethernet link:** look for link-down events: `ha host logs --lines 20000 | grep -i -E "<INTERFACE>|link is|carrier"`
  (get the interface name from `ha network info`).
  DHCP renewals on their own are normal.
- **Network interfaces:** check them with `ha network info`.

## 4. Find the cause in the logs

- **Integration errors:** `ha core logs | grep -i <integration>`. Note that the log only covers the time since
  the last restart.
- **Recent updates:** check for one with `ha core info`.
  - **If an update broke something:** search the exact error text together with the version number. A known
    regression usually has an issue on GitHub and a fix in the next patch.
  - **Fix it:** `ha core update --version <next> --backup`, or roll back to the last version that worked.
- **Need more detail:** turn on debug logging for just that integration with `logger.set_level`, wait for the
  next drop, then read the log. The level goes back to normal on the next restart.
- **Stuck integration:** reload it with `POST /api/config/config_entries/entry/<id>/reload`. If it's still in
  `setup_retry`, the cause is deeper than a temporary glitch.

## 5. Show it honestly on the dashboard

- **Separate integration-wide blips from device drops:** one "UniFi connection: N blips" row, plus per-device
  dropouts that leave out the drops during those blips.
- **Add a plain-language note** explaining what each kind means.
- **Expected blips:** amber only above a sensible threshold (e.g. more than 3 in 24 h), so normal cloud
  refreshes don't look alarming.

## 6. Report to the owner

- **A table:** each device, its dropouts, their typical length, and what's actually happening.
- **What it isn't:** be clear about what you ruled out (e.g. "the Pi's link never went down").
- **What's still unknown:** say what you set up to find it (debug logging), and when to check back.
