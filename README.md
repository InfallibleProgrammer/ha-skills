# Home Assistant home-setup skills

Skills for Claude (Claude Code or another agent that reads `SKILL.md` folders) to help set up a Home Assistant
smart home from scratch: getting connected, UniFi network monitoring, secure remote access, a custom dashboard
with an illustration of the home and a clickable floor plan, solar and energy, devices, users and troubleshooting.

They contain no one's personal details. Every address, name, password and token is a placeholder that Claude
asks the owner for.

## Install

Copy the skill folders you want into `~/.claude/skills/` (for all projects) or `<project>/.claude/skills/`
(for one project). Each folder holds a `SKILL.md` plus any helper scripts or templates.

## Suggested order

| # | Skill | What it covers |
|---|-------|----------------|
| 1 | `home-assistant-foundations` | Installing Home Assistant OS, access (token, SSH, API), backups, safe updates, helper scripts |
| 2 | `unifi-network` | UniFi integration, an IoT VLAN, which controls to keep or turn off, live speeds, Network dashboard |
| 2b | `unifi-vlan-firewall` | Splitting the network into Main / IoT / Cameras / Servers VLANs, recommending where each device goes, and locking it down with legacy firewall rules (guided script with a dry run) |
| 3 | `remote-access-tailscale` | Remote access with no open ports, HTTPS, reverse-proxy trust, guest access rules |
| 3b | `local-https-letsencrypt` | A trusted HTTPS address at home: Let's Encrypt DNS challenge (Porkbun example), router local DNS, NGINX proxy, renewal and expiry alert |
| 4 | `users-and-presence` | Family accounts, permissions limits, phones for home/away |
| 5 | `smart-home-devices` | Lights, a virtual lock or garage, HomeKit bridge, appliances, automations, plant care |
| 6 | `solar-and-energy` | Solar inverters and gateways, forecast, time-of-use prices, Energy dashboard |
| 7 | `custom-dashboard-cards` | Building one custom-card file, a local preview harness, a deploy script, versioning |
| 8 | `building-illustration` | Drawing the owner's actual building from photos, map links and builder drawings |
| 9 | `floor-plan-card` | Tracing the floor plan into a clickable card that toggles lights and shows the vacuum |
| 10 | `troubleshooting-dropouts` | Working out why devices "go unavailable" when the network looks fine |

## How these skills work with the owner

- Ask before anything that's hard to undo: deleting things, turning off network ports, changing who can reach
  Home Assistant, updating or rolling back Home Assistant.
- Never put tokens, passwords or API keys in files, dashboards or chat logs. Ask the owner to enter them in the
  Home Assistant UI, or pass them through environment variables. If a token gets pasted into chat, suggest
  replacing it.
- Make one change at a time, show a preview, then deploy. Keep a numbered copy of every version, so you can go
  back exactly as many steps as asked.
