---
name: smart-home-devices
description: Add common smart-home devices to Home Assistant and make them useful. Covers lighting bridges and hubs, virtual lock or garage controls built from helpers, HomeKit Bridge exposure, cloud appliances (washers, ovens, cooktops, water heaters, robot vacuums), light automations with timers, and a plant-watering tracker. Use when someone is adding devices, wants a lock or garage that Siri or HomeKit can control, or wants automations or reminders.
---

# Smart-home devices

## Start with an inventory

Cover only what the owner actually has. Brands below are examples, not assumptions: ask, then check that
brand's integration page.

Ask the owner to list every device with its brand and model, its room, and how it connects: wired, Wi-Fi,
Thread or Matter, Zigbee, or a cloud account.
- Use their **room names as Home Assistant areas**. Lights grouped by area power the floor plan and the
  window lighting later.
- Check each device's page on home-assistant.io for what it actually supports. Many cloud appliances only
  report status and can't be controlled.

## Lighting bridge or hub (e.g. Lutron Caséta, Philips Hue, a Zigbee or Matter hub)

- **Add the bridge:** add the integration and press the button on the bridge when asked.
- **Give the bridge a fixed address:** reserve its IP in the router. If it lives on an IoT VLAN, Home Assistant
  needs a way to reach it (see the `unifi-network` skill).
- **Name lights by room:** this gives `light.<room>_<room>_main_lights` style IDs, which are easy to group.
- **If every light goes "unavailable" at once,** check the integration first (Settings → Devices & services)
  before blaming the network.
  - **Look for:** `setup_retry` with "Timed out on connect", and TLS errors in `ha core logs`.
  - **Likely cause:** a Home Assistant update. Search the error text plus the version, then update to the next
    patch or roll back.

## Virtual lock or garage door (when the real device isn't in Home Assistant yet)

These let you build the dashboard, automations and HomeKit/Siri controls now, and swap in the real device
later:
- **Lock:** an `input_boolean` (on = locked), wrapped in a **template lock** that reads the boolean and turns
  it on or off.
- **Garage door:** an `input_boolean` (on = open), wrapped in a **template cover** (device class `garage`) with
  open and close actions.
- **When the real device arrives:** point the template actions at it, or replace the template.

## HomeKit Bridge (Siri, Apple Home)

- **Expose only what's needed:** choose the entities you include. Each bridge pairs once using the QR code in
  its notification.
- **Locks and garage doors:** Apple asks for confirmation for these. Some owners prefer exposing the simple
  switch helpers, which skip that confirmation. That's a deliberate trade-off, so explain it and let them
  choose.
- **Avoid double exposure:** if there are two bridges, leave the lock and garage out of the second one.

## Light automation pattern: "on, then off after N minutes"

Use a **timer helper**, not a delay, so restarts and repeated triggers behave:
- **Trigger:** the door opens, motion is detected, or someone arrives after sunset.
- **Action:** turn the light on, then `timer.start` with the duration.
- **Second trigger, `timer.finished`:** turn the light off.
- **Restarting the timer** on each new trigger extends it automatically.

## Cloud appliances: what to expect

- **Washers and dryers (often via a brand cloud such as SmartThings, LG ThinQ or Home Connect):** state, remaining time and alerts.
  - Short "unavailable" blips every ~50 minutes are a cloud refresh. They're harmless.
- **Ovens and ranges:** state, mode and temperature. Remote start can be limited, so test it before
  you rely on it.
- **Cooktops:** often connectivity and alerts only. Enable the alert
  sensors.
- **Water heaters (often a brand cloud):** mode, temperature and available hot water.
  - Cloud reconnects cause ~15–20 s drops. Frequent drops also point to weak Wi-Fi where the heater is (often
    a garage).
- **Robot vacuums:** state, current room, room cleaning and a map.
  - A button helper plus an automation makes one-tap routines such as "vacuum kitchen and living room".
- **TVs:** they often go "unavailable" in deep standby. That's normal.

## Plant-watering tracker (no sensors needed)

- **For each plant:** create an `input_datetime` helper, "Plant <name> watered" (date only).
- **For plants with a dormant season:** add an `input_boolean` "dormant" switch.
- **Ask for a care guide:** the owner's plant list or a care PDF, to get each plant's watering interval in
  summer and winter and a "check before watering" hint.
- **The card:** shows days since watering against the interval, with a tap for "watered today".
  - Make the helper names match the plant IDs, so a deploy script can create any that are missing.
