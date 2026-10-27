---
name: unifi-network
description: Connect a UniFi network (gateway, switches, access points) to Home Assistant and build a Network dashboard. Covers creating a local UniFi account, installing the integration, letting Home Assistant reach an IoT VLAN, deciding which controls to keep or turn off, enabling useful sensors (latency, temperatures, live WAN speeds), and spotting UniFi connection blips. Use when someone has UniFi gear and wants it in Home Assistant, or asks about network monitoring, an IoT VLAN, PoE or port controls.
---

# UniFi network in Home Assistant

## 0. Ask first

1. **Hardware:** which gateway (UCG, UDM, UXG or Cloud Key) and which switches and APs they have.
2. **Network layout:** do they have separate networks or VLANs (main, IoT, cameras)? Which subnet is Home
   Assistant on, and which one are the smart devices on?
3. **Safety rules:** which controls must **never** be exposed? Typical answers: no Wi-Fi on/off, no "regenerate
   Wi-Fi password", and no turning off the gateway or the port that feeds the core switch. A power cycle may be
   OK. Write their answers down and follow them.

## 1. Create a local UniFi account for Home Assistant

In UniFi Network → Settings → Admins & Users → Add admin:
- choose **Restrict to local access only** (no cloud or SSO account, and no 2FA prompt),
- set the role to **Site Admin** (Home Assistant needs it to read everything and power-cycle ports),
- and use a unique username and a long password, which the owner types into Home Assistant themselves.

## 2. Install the integration

Settings → Devices & services → Add integration → **UniFi Network**.
- **Host:** the gateway's IP address. **Port:** 443. Leave **Verify SSL** off, since the gateway uses a
  self-signed certificate.
- **Area names:** Home Assistant may prefix entity IDs with the area name (`sensor.<area>_<device>_...`). Check
  the real IDs in the entity registry before you write any dashboard config.

## 3. Let Home Assistant reach the IoT VLAN (if devices live there)

Home Assistant OS can join the IoT VLAN directly, so local integrations (solar gateways, bridges, Matter) can
see devices without firewall holes:
Find the Ethernet interface name first with `ha network info` (it differs by hardware, e.g. `end0`, `eth0`, `enp1s0`).
```bash
ha network vlan <INTERFACE> <VLAN_ID> --ipv4-method static --ipv4-address <IOT_IP>/24   # no gateway: stays non-routed
```
- **No gateway on the VLAN interface:** leave it off, so the main network stays the default route.
- **mDNS conflict on two networks:** Home Assistant can then end up as "homeassistant-2", repeatedly
  re-announcing its name. The fix:
  `ha network update <vlan_iface> --mdns resolve --llmnr resolve`. Then set the hostname back to
  `homeassistant` in Settings → System → Network.
- **Firewall rules:** in UniFi, allow traffic **from** Home Assistant to the IoT devices it needs, and keep IoT
  blocked from the main network.

For splitting the network into Main / IoT / Cameras / Servers VLANs with firewall rules, use the
`unifi-vlan-firewall` skill and its guided script.

## 4. Decide what to keep (ask the owner)

The integration creates many switches and buttons. Go through them with the owner:

| Entity type | Recommendation |
|-------------|----------------|
| Wi-Fi network on/off switches, "regenerate password" buttons | **Turn these off** (entity registry: `disabled_by: user`). |
| Port enable/disable switches on links between UniFi devices (gateway↔switch, uplinks) | Turn off. Switching one off can cut the whole house off. |
| PoE switches and **power-cycle** buttons for ports feeding UniFi devices (APs, small switches) | Keep these on the upstream end of the link. A power cycle is a safe way to unstick an AP. |
| Port controls for non-UniFi devices (TV, game console, NAS) | Usually turn off, unless the owner wants them. |
| Per-client tracking (`device_tracker.*`) | Keep. It's useful for "is device X connected". |
| WAN latency, gateway temperatures, CPU and memory, client counts, uptime | **Turn on**. Some are off by default. |
| Port link speed, PoE power | Turn on for the ports you show on the dashboard. |

**How to disable or enable an entity:** send `config/entity_registry/update` with
`{"entity_id": ..., "disabled_by": "user"}` to disable, or `null` to enable. Enabling takes effect after the
integration reloads, about 30 seconds later, or right away if you reload it yourself.

**Temperatures in the owner's preferred unit:** set `options.sensor.unit_of_measurement` through the entity
registry.

## 5. Live upload and download speeds

The UniFi integration has no "WAN throughput" sensor, but it does have **per-port bandwidth RX/TX** sensors:
1. **Turn on the bandwidth option:** UniFi integration options → expand the extra options → turn on **"Bandwidth
   sensors"** (`allow_bandwidth_sensors`).
2. **Turn off the per-client sensors it creates:** this also creates RX/TX sensors for **every client**, which
   are on by default. Disable those in the registry unless the owner wants them.
3. **Enable the WAN port's two sensors:** both are off by default. On the WAN port, **RX = download** and
   **TX = upload**. Rename them to clear IDs, e.g. `sensor.<gateway>_wan_download` and `..._wan_upload`.
4. **Explain how live they are:** the values update whenever the gateway sends stats, about every 10–30 s.
   That's near-live, not second-by-second. They report in Mbit/s.

## 6. Network dashboard (see the `custom-dashboard-cards` skill for the card framework)

Recommended views:
- **Overview:**
  - a headline status line ("Everything is online" / "<device> is offline" / "Internet is slow"),
  - latency to Cloudflare, Google and Microsoft,
  - live ↓/↑ speed tiles,
  - the plan speed and fiber port speed,
  - gateway CPU temperature, firmware updates waiting, and restarts in the last 7 days (from each device's
    uptime),
  - and history graphs of latency over 24 h and traffic over 6 h.
- **Topology:** gateway → switches → APs, with link speed and PoE watts on each link.
- **Devices:** a card per device, with a two-tap confirmation before a power cycle.
- **Ports & PoE:** only the ports that are actually used.
- **Smart home:** how each smart device connects (wired IoT, Wi-Fi, which cloud), plus dropouts in the last
  24 h.

Describe the house's real wiring in the card config (which port feeds which device, and what's PoE-powered).
Ask the owner; don't guess.

## 7. UniFi connection blips (important when reading dropout counts)

Every so often, Home Assistant's live connection to the UniFi gateway drops for about 10–20 s and reconnects.
When that happens, **every** UniFi entity goes unavailable at the same second: the gateway, APs, switches and
all client trackers. The devices themselves never disconnected, which is why the UniFi app shows everything
as fine.
- **Detect it:** watch one always-present UniFi entity, such as the gateway uptime sensor. Any "unavailable"
  moment on it is a blip.
- **Show it separately:** on the dashboard, put a single "UniFi connection: N blips in 24 h" row, and don't
  count a device's drops within ~90 s of a blip against that device.
- **Find the cause:** turn on debug logging with `logger.set_level`, using
  `{"homeassistant.components.unifi": "debug", "aiounifi.websocket": "debug"}`. Then read `ha core logs`
  after the next blip. The level goes back to normal on the next restart.
