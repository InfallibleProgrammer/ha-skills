---
name: remote-access-tailscale
description: Give secure remote access to Home Assistant with Tailscale, without opening router ports. Covers the add-on, an HTTPS address through Tailscale Serve, the reverse-proxy trust Home Assistant needs, external and internal URLs for the phone app, access rules that keep other tailnet users and devices out, family access, and fixing phones that can't connect. Use when someone wants to reach Home Assistant away from home, or asks about Tailscale, remote access, port forwarding or Nabu Casa.
---

# Remote access with Tailscale

## Options to offer

- **Nabu Casa (Home Assistant Cloud):** a paid subscription and the easiest choice. It also gives voice
  assistants.
- **Tailscale:** free, with no open ports, and only devices signed into the owner's tailnet can reach Home
  Assistant. Recommended if they're comfortable installing an app on each phone. The steps below cover it.
- **Port forwarding with a public domain:** avoid it unless they really know what they're doing.

## 1. Install and sign in

Settings → Add-ons → Add-on store → **Tailscale** (community add-on) → Install → Start → open the log, follow the
login link, and approve the machine in the Tailscale admin console.

Add-on options to set:
- `share_homeassistant: serve` and `share_on_port: 443`. This gives you
  `https://<machine>.<tailnet>.ts.net` with a real certificate.
- `advertise_routes: []` unless they want subnet routing, and keep the exit node off unless they ask for it.
- In the Tailscale admin console, turn on **MagicDNS** and **HTTPS certificates**, and turn **off key expiry**
  for the Home Assistant machine.

## 2. Make Home Assistant trust the add-on as a reverse proxy

Without this, Serve fails and the add-on may stop with
"Unable to connect to Home Assistant as reverse proxy".
- Turn on `use_x_forwarded_for: true` and set `trusted_proxies: 127.0.0.1/32, ::1/128`.
- **On newer releases these are UI settings** (Settings → System → Network → HTTP), not YAML. A leftover
  `http:` block in `configuration.yaml` is ignored and raises a repair notice.
- **Over the API:** `http/config/configure` restarts Home Assistant in trial mode, then `http/config/promote`
  keeps the change. Without promoting, it reverts on its own.
- **Check it worked:** from a device on the tailnet, `curl -I https://<machine>.<tailnet>.ts.net` should
  return HTTP 200.

## 3. URLs

Settings → System → Network:
- **Internal URL:** `http://<HA_IP>:8123`.
- **External URL:** `https://<machine>.<tailnet>.ts.net`.

## 4. The phone app

1. Install Tailscale on the phone, sign in, and turn the VPN on.
   - Use "Use Tailscale DNS" (MagicDNS) so the `.ts.net` name resolves.
   - iCloud Private Relay or another VPN can get in the way, so turn it off to test.
2. In the Home Assistant app, open Settings → Companion app → server:
   - **External URL:** the ts.net address.
   - **Internal URL:** the local address.
   - **Home network:** the home Wi-Fi name (SSID), so the app uses the local address when the phone is home.
3. **Troubleshooting order:** turn off Wi-Fi on the phone, then open `http://<HA_tailscale_IP>:8123` in Safari.
   - **If it loads:** the problem is DNS or the app's URLs.
   - **If it doesn't:** check the Tailscale admin console to see whether the phone is online, and look at the
     access rules.

## 5. Access rules: only the right people and devices

The default tailnet policy lets everyone reach everything. If the owner shares the tailnet (with a friend's
PC, IT support or a guest), lock it down:
- **Admins only:** grant all access to `autogroup:admin` only.
- **Tag other machines:** give shared machines a tag (for example `tag:guest`). Tagged devices stop belonging
  to a user and only get what the rules grant them.
- **Test the rules:** add policy `tests` that prove guests are **denied** access to Home Assistant and to the
  owner's computers. For example, `{"src": "tag:guest", "deny": ["<HA_tailscale_IP>:8123"]}`.
- **Family members:** invite them to the tailnet, then grant only Home Assistant:
  `{"src": ["<their email>"], "dst": ["<HA_tailscale_IP>"], "ip": ["tcp:443", "tcp:8123"]}`.

## 6. Clean up

- **The Tailscale integration:** if a Home Assistant "Tailscale" integration was added only to try it out,
  remove it, and revoke its API key in the Tailscale admin console.
- **Later, local HTTPS:** a Let's Encrypt certificate using a DNS-01 challenge, with no open ports, plus a
  local DNS record in the router. Mention it as a possible next step and add it to the to-do file. The
  `local-https-letsencrypt` skill has the steps.
