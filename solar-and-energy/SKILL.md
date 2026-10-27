---
name: solar-and-energy
description: Bring rooftop solar, house consumption and electricity prices into Home Assistant. Covers local solar gateways (SunPower PVS and similar) reached on an IoT network, a solar forecast, time-of-use price sensors for the owner's tariff, export credit and net-metering rules, the Energy dashboard, and custom solar cards (live flow, today, per-panel array, trends). Use when someone has solar panels, a home battery or EV charging, or wants to see costs and usage.
---

# Solar and energy

## 1. Ask

- **Equipment:** which inverter or monitoring gateway they have (SunPower PVS, Enphase Envoy, SolarEdge, Tesla
  Gateway, ...), how many panels and of what wattage, and the system size, roof direction (azimuth) and tilt.
- **Network:** is the gateway on the home network, an IoT VLAN, or only on a direct cable? Some gateways only
  answer local requests from certain networks or ports, so check that brand's integration docs.
- **Utility plan:** the utility and rate plan (e.g. a time-of-use EV plan), the season boundaries, the
  peak/part-peak/off-peak hours, prices per kWh, and the net-metering version, which sets how exports are
  credited.
  - Prices change, so ask for a recent bill or the utility's rate sheet. Don't make them up.

## 2. Get the data in

- **Local integration first:** use the gateway's local integration (HACS or built-in) and poll gently.
  - A gateway that drops its Wi-Fi or Ethernet will need a "poll success rate" or connectivity sensor on the
    dashboard.
- **If the gateway is on an IoT VLAN:** give Home Assistant an interface on that VLAN (see the `unifi-network`
  skill).
- **Forecast:** add **Forecast.Solar** with the system's kW, azimuth (180 = south) and tilt.
- **Price sensors:** create template sensors for the **current buy price** and the **current export credit**,
  using the time of day, the weekday or holiday, and the season.
  - Keep the rate table in one place, so a rate change is a one-line edit.

## 3. Energy dashboard

Settings → Dashboards → Energy:
- **Grid consumption and return:** use energy sensors with `state_class: total_increasing`, in kWh.
- **Prices:** attach the price entities for consumption and return.
- **Solar production:** add it, and attach the Forecast.Solar forecast to it.
- **Before changing it:** back up the current energy preferences, using WebSocket `energy/get_prefs`.

## 4. Custom solar cards (see `custom-dashboard-cards`)

- **Flow:** solar → house → grid in real time, with arrows that flip when exporting.
- **Today:** produced, used, exported and imported, plus what it cost or saved at the current tariff.
- **Health:** offline panels or microinverters, gateway polling health, and panels producing well below their
  neighbours.
- **Array:** a picture of the real roof layout, with each panel coloured by its current watts. Ask for a
  photo or the installer's layout drawing.
- **Trends:** month by month, the best days, peak power and per-panel totals.
- **Rate card:** the current period, its price, when it changes next, and the cheapest upcoming window, which
  is useful for EV charging.

## Gotchas

- **Catch-up after an outage:** when a gateway comes back after being offline, it may report a lump of
  production all at once. Value that energy at an average price for the period, not the price at the moment it
  arrived.
- **Overnight drops are normal:** microinverters and panel sensors go "unavailable" at night. Don't count those
  as dropouts.
- **Recorder size is normally fine on an SSD.** If the database grows fast, exclude very chatty entities
  rather than turning recording off.
