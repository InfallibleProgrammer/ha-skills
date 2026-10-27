---
name: unifi-vlan-firewall
description: Split a UniFi home network into Main, IoT, Cameras and Servers VLANs and lock it down with legacy UniFi firewall rules. Inventories the devices already on the network and recommends which network each belongs on, asks for the server's IP address and which IoT devices (if any) may reach it, then creates the networks, groups and rules with a guided script (a dry run first). Use when someone wants to segment their UniFi network, isolate IoT or a home server, block cameras from the internet, or audit their firewall rules.
---

# UniFi VLANs and firewall

## The target layout

| Network | VLAN | Example subnet | What goes on it | Internet |
|---------|------|----------------|-----------------|----------|
| Default / Management | none | (existing) | UniFi gateway, switches, APs | yes |
| Main / Trusted | 10 | x.x.10.0/24 | Phones, laptops, tablets, Apple TV / HomePod (home hubs), consoles, Home Assistant | yes |
| IoT | 20 | x.x.20.0/24 | Plugs, thermostats, appliances, TVs, bridges, vacuums, printers, solar/EV | yes |
| Cameras | 30 | x.x.30.0/24 | UniFi Protect and other IP cameras | **no** |
| Servers | 40 | x.x.40.0/24 | NAS, media servers, Docker hosts | yes |

**What the rules enforce:**
- **Main** can reach everything. Nothing can **start** a connection into Main; only replies come back.
- **IoT ↔ Servers** are blocked both ways. Optional per-device exceptions let a chosen IoT device reach the
  server on chosen ports, matched by MAC so they survive IP changes.
- **Servers** can't start connections to any local network. Main can still reach them.
- **Cameras** are isolated in both directions with no internet. Protect, running on the gateway, still works.
- **IoT and Servers** can only use DNS, DHCP, NTP, mDNS and ping **on the gateway itself**. They can't reach
  the console login or SSH. A hacked plug can't attack the router.
- **Plain RTSP (TCP 7447)** is refused for everyone. Protect also serves encrypted **RTSPS on 7441**, which is
  what Home Assistant and Scrypted use.

## Steps

1. **Check the firewall mode.** This skill writes **legacy** rules (Settings → Security → Firewall → "LAN In /
   LAN Local"). If the console shows **zone-based** policies (Policy Engine → Zones), build the same layout as
   zone policies in the UI instead. The script detects this and stops.
2. **Create a local admin** for the script: Settings → Admins & Users → Add admin → "Restrict to local access
   only". The owner types the password at the script's hidden prompt, so never ask for it in chat.
3. **Dry run** (read-only): `python3 scripts/unifi_vlan_setup.py --host <gateway IP> --user <local admin>`
   - It lists every connected device with a **recommended network and the reason** (matched by name or vendor).
   - **Go through the list with the owner.** Anything marked `?` needs their input. Typical judgement calls:
     - **Apple TV / HomePod:** Main. As home hubs they need to talk to the phones.
     - **TVs:** IoT.
     - **NAS:** Servers.
     - **Home Assistant:** Main, plus an IoT VLAN interface if it needs local IoT devices. See the
       `unifi-network` skill.
     - **UniFi gear:** stays on Management.
4. **Answer the questions:**
   - the address base (default `192.168`),
   - the **server's IP** (default `.40.10`) and its MAC, which reserves the IP,
   - and **which IoT devices may reach the server, on which ports.** Usually none. If the owner streams from
     an IoT-network box, allow only that box and only the media port, e.g. 8096 for Jellyfin or 32400 for
     Plex.
5. **Review the printed plan** with the owner: networks, groups, and the LAN In and LAN Local rules in order.
6. **Apply** it: re-run with `--apply` and type `yes`. Anything that already exists with the same name is kept,
   not overwritten.
7. **Move the devices.** The script doesn't do this:
   - **Wi-Fi:** create an IoT SSID on the IoT network (and a Protect SSID for Wi-Fi cameras). The owner sets the
     Wi-Fi passwords in the UI.
   - **Wired:** set each switch port's **Native VLAN** to the target network.
   - **Reconnect** devices. Re-reserve fixed IPs for anything that needs them (cameras, bridges, the server).
8. **Verify from each network:**
   - From an IoT device, the console page (`https://<gateway>`) is **refused**, DNS works, and the server is
     unreachable, except for the allowed devices.
   - From Main, the console and the server both work.
   - All cameras still record in Protect, and the Home Assistant integrations still report.

## Gotchas

- **Rule order matters:** legacy rules apply top-down. Allows (established/related, Main → X, exceptions) must
  sit **above** the drops. The script numbers them in that order after any existing rules. If the owner already
  has broad allow rules, review the final order in the UI.
- **Traffic to the gateway is "LAN Local", not "LAN In".** A LAN In rule with the gateway's own IP as the
  destination never matches. Protect, DNS and the console all live on the gateway.
- **Don't put Cameras in the "gateway lockdown" rules.** Cameras reach Protect on the gateway, so blocking them
  disconnects every camera unless the Protect ports are allowed first.
- **Docker addresses never reach the firewall.** Containers (172.17.x, Home Assistant's 172.30.x) appear as
  their host's LAN IP to the gateway, because Docker uses NAT. Macvlan containers get real LAN IPs, which the
  /16 groups already cover.
- **Server → NAS:** if the server mounts a NAS on another network, NFSv3 uses random helper ports. Mount with
  `nfsvers=4.1` so only TCP 2049 is needed, then allow just that port. Or put the NAS on the Servers network.
- **mDNS (AirPlay/HomeKit discovery)** only crosses networks where mDNS is turned on (Main and IoT here).
  Leave it off on Servers and Cameras.
- **IPv6:** these rules are IPv4. Keep IPv6 off on the internal networks, or add matching IPv6 rules.
- **Home Assistant on two networks:** if it has an interface on IoT, IoT devices can reach it without passing
  the firewall. Protect it with a strong password and two-factor login.
- **Test the plain RTSP block:** "Reject" refuses instantly, while "Drop" makes connections hang until they
  time out. Port 7447 should fail from every network.

## Auditing an existing setup

Read the rules: GET `rest/firewallrule`, `rest/firewallgroup` and `rest/networkconf` under
`/proxy/network/api/s/<site>/`. Map each network ID to its name, sort by ruleset and `rule_index`, and check
them against the table above.
- **Common findings:** IoT-wide exceptions to servers, a server allowed to start connections to a NAS on every
  port, and no LAN Local rules at all.
- **Show before and after:** test from the affected network, e.g. from a host with an IoT interface, check the
  console returns 200 before and is refused after.
