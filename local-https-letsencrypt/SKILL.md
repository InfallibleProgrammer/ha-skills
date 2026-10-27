---
name: local-https-letsencrypt
description: Give Home Assistant a real HTTPS address at home (for example https://ha.example.com:8443) with a free Let's Encrypt certificate, without opening any router ports. Covers a subdomain on a domain the owner already has (worked example Porkbun), a DNS-01 challenge with a tightly scoped API key, a local DNS record in the router (UniFi), the NGINX SSL proxy add-on, reverse-proxy trust, automatic renewal, an expiry alert, and the gotchas (registrar parking wildcards, port 443 already used by Tailscale Serve, no HTTP-to-HTTPS redirect). Use when someone wants local HTTPS, a trusted certificate, no browser warnings at home, or asks about Let's Encrypt, NGINX, DNS challenges or Porkbun.
---

# Local HTTPS with Let's Encrypt and NGINX

The result: `https://<SUB>.<DOMAIN>:<PORT>` works on the home network with a trusted certificate. Nothing is
exposed to the internet. The certificate is proven with a **DNS-01 challenge** (a temporary TXT record), so
Let's Encrypt never has to connect to the house.

Placeholders used below: `<DOMAIN>` (e.g. `example.com`), `<SUB>` (e.g. `ha`), `<HA_IP>` (Home Assistant's
LAN address), `<PORT>` (the HTTPS port NGINX listens on).

## 0. Ask first

1. **A domain:** do they own one, and where is its DNS hosted? The add-on supports many providers (Porkbun,
   Cloudflare, Namecheap, Route 53 …). Check the provider is in the Let's Encrypt add-on's list before going on.
2. **The subdomain name** they want (`<SUB>`). Use a name that isn't in use yet.
3. **Is port 443 on Home Assistant already taken?** The Tailscale add-on with `share_homeassistant: serve` on
   443 owns it. If so, NGINX goes on another port, typically **8443**. If not, 443 is fine and gives a URL
   with no port number.
4. **Which networks** should reach the address? The local DNS record decides that (step 3).

The owner types every API key and secret into the add-on UI themselves. Never put them in chat or files.

## 1. A scoped API key at the DNS provider (Porkbun example)

1. porkbun.com → **Domain Management** → the domain → **Details** → turn **API ACCESS** on for that domain.
   Without this, every API call fails even with a valid key.
2. Account → **API Access** → create a key. Limit it as much as the provider allows:
   - **Scopes:** DNS (plus Read if the provider requires it to look up records).
   - **Domains:** only `<DOMAIN>`.
   - **Allowed IPs:** the home's public IP. Find it with `curl -s https://ifconfig.me` from a home device.
     Note: if the ISP changes the home IP, renewals fail until the allowed IP is updated. Write this down.
3. The owner keeps the API key (`pk1_…`) and secret (`sk1_…`) to paste into the add-on in step 4.

## 2. Stop the registrar's parking wildcard from hijacking the name

Many registrars (Porkbun included) add parking records: an `ALIAS` on the bare domain and a **`CNAME` for
`*`** pointing at a parking host (e.g. `pixie.porkbun.com`). Even with a local A record, devices asking for
the **IPv6 (AAAA)** address get the wildcard CNAME, and browsers can end up at the parking page.

- **Check:** `dig +short AAAA <SUB>.<DOMAIN> @1.1.1.1` should print nothing. If it prints the parking host,
  fix it.
- **Fix (recommended):** add any record for the exact name in public DNS, for example a **TXT** record,
  host `<SUB>`, value `local only`. A wildcard never applies to a name that has its own records, so AAAA now
  returns empty. This publishes no address.
- **Alternative:** delete the `*` CNAME. That fixes every subdomain but removes the parking page for them.
- **Don't** publish a public A record with the LAN address unless the owner wants that; the TXT record is
  enough.

## 3. A local DNS record in the router (UniFi example)

UniFi Network → Settings → Routing → **DNS** (Local DNS records) → Create:
- **Domain:** `<SUB>.<DOMAIN>`, **Type:** A, **IP:** `<HA_IP>`.
- Pick `<HA_IP>` on the network the owner's devices use. If Home Assistant has an address on several VLANs,
  use the one on the main network. Devices whose DNS is blocked from the gateway (e.g. an isolated IoT VLAN)
  simply won't resolve the name, which is usually what you want.
- **Check** from a home device: `dig +short <SUB>.<DOMAIN>` → `<HA_IP>`. If it shows something else, the
  device isn't using the router for DNS (a VPN, iCloud Private Relay, or a custom DNS setting).

## 4. The Let's Encrypt add-on

Settings → Add-ons → Add-on store → **Let's Encrypt** → Install. Configuration (YAML mode):

```yaml
domains:
  - <SUB>.<DOMAIN>
email: <owner's email>          # expiry notices from Let's Encrypt
keyfile: privkey.pem
certfile: fullchain.pem
challenge: dns
dns:
  provider: dns-porkbun          # match the owner's provider
  porkbun_key: <owner pastes>
  porkbun_secret: <owner pastes>
  propagation_seconds: 120
```

Gotchas:
- **Delete fields for other providers.** The default config may contain `transip_global_key`. Since add-on
  v6.0.0 its presence stops the add-on ("transip_global_key is not supported"). Remove the line entirely.
- **`propagation_seconds: 120`:** the default is often too short for the TXT record to reach every
  nameserver, which shows up as an "incorrect TXT record" failure. 120 s is reliable.
- **Start it** and watch the log. Success ends with "Congratulations! Your certificate …" and the files land
  in `/ssl/fullchain.pem` and `/ssl/privkey.pem`. The add-on then stops; that's normal. It deletes the
  temporary `_acme-challenge` TXT record itself; check it's gone in the provider's DNS list.
- **Check the certificate** without showing the key:
  `openssl x509 -in /ssl/fullchain.pem -noout -subject -issuer -enddate` (from the SSH add-on).

## 5. The NGINX SSL proxy add-on

Settings → Add-ons → **NGINX Home Assistant SSL proxy** → Install. Configuration:

```yaml
domain: <SUB>.<DOMAIN>
certfile: fullchain.pem
keyfile: privkey.pem
hsts: max-age=31536000; includeSubDomains
cloudflare: false
customize:
  active: false
```

Network section (ports):
- **443/tcp:** set to `<PORT>`. If Tailscale Serve uses 443, the add-on can't start there ("port 443 is
  already in use"); use **8443**.
- **80/tcp:** leave **blank**. The add-on's port-80 redirect always sends people to `https://…` on 443,
  which is wrong when NGINX is on 8443 (it lands on Tailscale's certificate instead).

Start it, and turn on **Start on boot** and **Watchdog**.

## 6. Make Home Assistant trust NGINX

NGINX runs on the add-on network, `172.30.33.0/24`. Home Assistant rejects proxied requests (HTTP 400) until
that range is trusted:
- Settings → System → Network → HTTP (newer releases; older ones use the `http:` block in
  `configuration.yaml`): `use_x_forwarded_for: true`, `trusted_proxies` =
  `127.0.0.1/32`, `::1/128`, `172.30.33.0/24`. Keep any entries already there (Tailscale uses the first two).
- **Over the API:** `http/config/configure` restarts Home Assistant in trial mode, then
  `http/config/promote` keeps it. Without promoting, it reverts on its own.

## 7. URLs

Settings → System → Network:
- **Internal URL:** `https://<SUB>.<DOMAIN>:<PORT>`.
- **External URL:** unchanged (e.g. the Tailscale `ts.net` address).
- In each phone's Home Assistant app: Settings → Companion app → server → **Internal URL** → the same
  address, with the home Wi-Fi name as the home network.

## 8. Test

From a device on the home network:

```bash
curl -sI https://<SUB>.<DOMAIN>:<PORT> | head -1                     # HTTP/2 200 (or 405 for HEAD)
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $HA_TOKEN" \
  https://<SUB>.<DOMAIN>:<PORT>/api/                                  # 200 = proxy trust works
echo | openssl s_client -connect <SUB>.<DOMAIN>:<PORT> -servername <SUB>.<DOMAIN> 2>/dev/null \
  | openssl x509 -noout -issuer -enddate                             # Let's Encrypt, ~90 days out
```

Also confirm the plain address `http://<HA_IP>:8123` still works; it's the fallback if NGINX or the
certificate ever breaks.

**Tell the owner:** plain `http://<SUB>.<DOMAIN>…` does **not** redirect. Port 80 isn't listening, and
`http://` on `<PORT>` returns 400. They should bookmark the full `https://…:<PORT>` address.

## 9. Renewal and an expiry alert

Let's Encrypt certificates last 90 days and the add-on only renews within 30 days of expiry, so it's safe to
run it weekly. NGINX must restart to load a new certificate.

1. **Certificate expiry sensor:** Settings → Devices & services → Add integration → **Certificate Expiry**,
   host `<SUB>.<DOMAIN>`, port `<PORT>`. It creates `sensor.<sub>_<domain>_<port>_cert_expiry` (check the
   real ID in the entity registry).
2. **Weekly renewal:**

```yaml
alias: Let's Encrypt weekly renewal check
triggers:
  - trigger: time
    at: "03:30:00"
conditions:
  - condition: time
    weekday: [mon]
actions:
  - action: hassio.addon_start
    data: { addon: core_letsencrypt }
  - delay: "00:06:00"
  - action: hassio.addon_restart
    data: { addon: core_nginx_proxy }
mode: single
```

3. **Alert if it's close to expiring or unreadable:**

```yaml
alias: Let's Encrypt certificate expiring or unreadable
triggers:
  - trigger: time
    at: "09:00:00"
conditions:
  - condition: template
    value_template: >-
      {% set s = states('sensor.<CERT_EXPIRY_SENSOR>') %}
      {{ s in ['unavailable', 'unknown'] or
         (as_datetime(s) - now()).days < 21 }}
actions:
  - action: persistent_notification.create
    data:
      title: HTTPS certificate needs attention
      message: >-
        The certificate for <SUB>.<DOMAIN> expires {{ states('sensor.<CERT_EXPIRY_SENSOR>') }}.
        Check the Let's Encrypt add-on log. A common cause is the home IP changing, which the DNS
        provider's API key allowlist then rejects.
  - action: notify.mobile_app_<OWNER_PHONE>
    data:
      title: HTTPS certificate needs attention
      message: Check the Let's Encrypt add-on log in Home Assistant.
mode: single
```

Test the condition once (Developer tools → Template) and confirm it's `false` with ~90 days left.

## 10. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Let's Encrypt log: "transip_global_key is not supported" | Delete that line from the config (step 4). |
| "Incorrect TXT record" / DNS problem | Raise `propagation_seconds`; check API ACCESS is on for the domain. |
| Provider API: invalid key / forbidden | Wrong key or secret, the key isn't allowed for this domain, or the home IP changed. |
| NGINX won't start, port in use | Tailscale Serve (or something else) owns 443; use 8443. |
| Browser shows the registrar's parking page | The wildcard CNAME wins for AAAA; add the TXT record (step 2). |
| HTTP 400 through NGINX, direct :8123 works | `172.30.33.0/24` isn't in trusted proxies (step 6). |
| Name doesn't resolve on one device | That device isn't using the router's DNS (VPN, Private Relay, custom DNS). |
| Works, but certificate expired | NGINX wasn't restarted after renewal, or renewal failed; check both add-on logs. |

## Notes for the to-do file

Record: the address, the port and why, the certificate expiry date, the API key's limits (scopes, domain,
allowed IP), "don't delete the `<SUB>` TXT record", the two automation names, and "if renewal fails, check
the home IP first".
