#!/usr/bin/env python3
"""Guided UniFi VLAN + legacy-firewall setup for a home network.

Builds the layout: Main (trusted), IoT, Cameras, Servers (+ the existing default/Management network), with
legacy firewall rules so that:
  - Main may reach everything; nothing may start connections into Main except replies.
  - IoT and Servers can't reach each other (optional per-device IoT -> Server exceptions).
  - Servers can't start connections to any local network.
  - Cameras are isolated both ways (Protect on the gateway still works) and have no internet.
  - IoT and Servers can only use DNS/DHCP/NTP/mDNS/ping on the gateway itself (no console login).
  - Plain, unencrypted RTSP from Protect (TCP 7447) is refused for everyone.

Safe by default: it only reads and prints a plan. Nothing changes without --apply AND a typed "yes".
Standard library only. Works with UniFi OS consoles (UCG, UDM, UXG, Cloud Key Gen2+) that use the LEGACY
firewall ("Firewall Rules": LAN In / LAN Local). It stops if the console uses zone-based firewall policies.

Usage:
  python3 unifi_vlan_setup.py --host 192.168.1.1 --user ha-local            # dry run: inventory + plan
  python3 unifi_vlan_setup.py --host 192.168.1.1 --user ha-local --apply    # make the changes
  python3 unifi_vlan_setup.py --clients-json clients.json                    # offline: recommendations only
The password is read with a hidden prompt (or $UNIFI_PASSWORD). It is never written anywhere.
"""
import argparse
import getpass
import http.cookiejar
import ipaddress
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

# ─── Plan defaults (the template; every value can be changed at the prompts) ──────────────────────────

NETWORKS = [
    # key, name, vlan, third octet, internet, mDNS, purpose of the network
    ('main', 'Main / Trusted', 10, 10, True, True, 'phones, laptops, tablets, Apple TV / HomePod hubs, game consoles, Home Assistant'),
    ('iot', 'IoT', 20, 20, True, True, 'smart plugs, thermostats, appliances, TVs, bridges, vacuums, printers, solar/EV gear'),
    ('cameras', 'Cameras', 30, 30, False, False, 'UniFi Protect and other IP cameras/doorbells (no internet)'),
    ('servers', 'Servers', 40, 40, True, False, 'NAS, media servers, Docker hosts, anything exposing services'),
]
GATEWAY_SERVICE_PORTS = ['53', '67', '68', '123', '5353']   # DNS, DHCP, NTP, mDNS
PLAIN_RTSP_PORT = '7447'
PRIVATE_RANGES = ['192.168.0.0/16', '172.16.0.0/12', '10.0.0.0/8']

# Keyword hints for recommending a network. Matched against the client's name, hostname and vendor (OUI).
HINTS = [
    ('cameras', ['camera', 'doorbell', 'g4-', 'g5-', 'g6-', 'protect', 'reolink', 'amcrest', 'hikvision', 'dahua',
                 'wyze', 'arlo', 'eufy', 'blink', 'ring-', 'axis']),
    ('servers', ['nas', 'unas', 'synology', 'diskstation', 'qnap', 'truenas', 'unraid', 'plex', 'jellyfin', 'emby',
                 'server', 'docker', 'proxmox', 'esxi', 'nuc', 'homelab']),
    ('main', ['iphone', 'ipad', 'macbook', 'imac', 'mac-mini', 'macmini', 'mac', 'android', 'pixel', 'galaxy',
              'laptop', 'desktop', 'pc', 'windows', 'surface', 'watch', 'apple tv', 'appletv', 'homepod',
              'playstation', 'xbox', 'nintendo', 'switch', 'steam']),
    ('iot', ['plug', 'kasa', 'tp-link', 'tplink', 'shelly', 'tuya', 'espressif', 'esp32', 'esp8266', 'wemo',
             'meross', 'govee', 'wiz', 'lifx', 'hue', 'lutron', 'caseta', 'bond', 'myq', 'chamberlain', 'tstat',
             'ecobee', 'nest', 'honeywell', 'sensi', 'thermostat', 'washer', 'dryer', 'samsung', 'lg', 'whirlpool',
             'bosch', 'miele', 'ge appliance', 'econet', 'rheem', 'roborock', 'roomba', 'irobot', 'ecovacs',
             'vacuum', 'tv', 'webos', 'roku', 'vizio', 'tizen', 'chromecast', 'fire tv', 'sonos', 'printer',
             'brother', 'epson', 'canon', 'hp ', 'pvs', 'sunpower', 'enphase', 'envoy', 'solaredge', 'tesla',
             'wallbox', 'chargepoint', 'emporia', 'tonal', 'peloton', 'wiced', 'hob', 'oven', 'fridge']),
]
# Ubiquiti network gear stays on the default / Management network.
UBIQUITI = ['ubiquiti', 'unifi', 'u6-', 'u7-', 'uap', 'usw', 'udm', 'ucg', 'uxg']


def recommend(c):
    """Return (network key, reason) for one client record from UniFi."""
    text = ' '.join(str(c.get(k) or '') for k in ('name', 'hostname', 'oui', 'dev_vendor', 'dev_cat')).lower()
    if any(k in text for k in UBIQUITI) and not any(k in text for k in HINTS[0][1]):
        return 'management', 'Ubiquiti network device (leave on the default/Management network)'
    for key, words in HINTS:
        hit = next((w for w in words if w in text), None)
        if hit:
            return key, f'matched "{hit.strip()}"'
    return '?', 'unknown: ask the owner what this is'


# ─── UniFi API (legacy Network application endpoints) ─────────────────────────────────────────────────

class UniFi:
    def __init__(self, host, user, password, site='default'):
        self.base = f'https://{host}'
        self.site = site
        ctx = ssl._create_unverified_context()   # consoles use a self-signed certificate
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx),
                                              urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = ''
        r = self._req('POST', '/api/auth/login', {'username': user, 'password': password}, raw=True)
        self.csrf = r.headers.get('X-Csrf-Token') or r.headers.get('x-csrf-token') or ''

    def _req(self, method, path, body=None, raw=False):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={'Content-Type': 'application/json', 'X-Csrf-Token': self.csrf})
        try:
            r = self.op.open(req, timeout=20)
        except urllib.error.HTTPError as e:
            raise SystemExit(f'UniFi API {method} {path} failed: HTTP {e.code} {e.read()[:300]!r}')
        return r if raw else json.load(r)

    def get(self, endpoint):
        return self._req('GET', f'/proxy/network/api/s/{self.site}/{endpoint}').get('data', [])

    def post(self, endpoint, body):
        r = self._req('POST', f'/proxy/network/api/s/{self.site}/{endpoint}', body)
        if r.get('meta', {}).get('rc') != 'ok':
            raise SystemExit(f'UniFi refused {endpoint}: {r.get("meta")}')
        return r['data'][0]

    def put(self, endpoint, body):
        r = self._req('PUT', f'/proxy/network/api/s/{self.site}/{endpoint}', body)
        if r.get('meta', {}).get('rc') != 'ok':
            raise SystemExit(f'UniFi refused {endpoint}: {r.get("meta")}')
        return r['data'][0]

    def zone_based(self):
        """True if the console uses zone-based firewall policies (this script only does legacy rules)."""
        try:
            r = self._req('GET', f'/proxy/network/v2/api/site/{self.site}/firewall-policies')
        except SystemExit:
            return False
        return isinstance(r, list) and any(not p.get('predefined') for p in r)


# ─── Prompts ──────────────────────────────────────────────────────────────────────────────────────────

def ask(q, default=''):
    a = input(f'{q}{f" [{default}]" if default else ""}: ').strip()
    return a or default


def yes(q):
    return ask(q + ' (yes/no)', 'no').lower() in ('y', 'yes')


# ─── Plan ─────────────────────────────────────────────────────────────────────────────────────────────

def show_inventory(clients):
    rows = []
    for c in clients:
        key, why = recommend(c)
        rows.append((key, c))
        name = c.get('name') or c.get('hostname') or '(no name)'
        print(f"  {name[:28]:28} {c.get('ip', '-'):15} {('wired' if c.get('is_wired') else c.get('essid') or 'wifi')[:14]:14} "
              f"{(c.get('oui') or '')[:16]:16} -> {key:10} {why}")
    return rows


def build_plan(base, server_ip, server_mac, exceptions):
    """Everything to create, in order. base = first two octets, e.g. '192.168'."""
    nets = [dict(key=k, name=n, vlan=v, subnet=f'{base}.{o}.1/24', internet=i, mdns=m, about=a)
            for k, n, v, o, i, m, a in NETWORKS]
    groups = [
        dict(name='RFC1918 Group', group_type='address-group', group_members=PRIVATE_RANGES),
        dict(name='All Home Networks', group_type='address-group', group_members=[f'{base}.0.0/16']),
        dict(name='IoT + Servers', group_type='address-group',
             group_members=[n['subnet'].replace('.1/24', '.0/24') for n in nets if n['key'] in ('iot', 'servers')]),
        dict(name='Gateway basic services', group_type='port-group', group_members=GATEWAY_SERVICE_PORTS),
        dict(name='RTSP Unencrypted Port', group_type='port-group', group_members=[PLAIN_RTSP_PORT]),
    ]
    # Legacy rules. src/dst use: ('net', key) | ('group', name) | ('addr', ip) | ('mac', mac) | None (any).
    lan_in = [
        dict(name='Allow Established and Related', action='accept', est=True),
        dict(name='Allow Main to Cameras', action='accept', src=('net', 'main'), dst=('net', 'cameras')),
        dict(name='Allow Main to Servers', action='accept', src=('net', 'main'), dst=('net', 'servers'), new=True),
    ]
    for e in exceptions:
        lan_in.append(dict(name=f'Allow IoT {e["name"][:20]} to Server', action='accept', protocol='tcp_udp',
                           src=('mac', e['mac']), dst=('addr', server_ip), port=e['ports']))
    lan_in += [
        dict(name='Block Server to Local Networks', action='drop', src=('net', 'servers'), dst=('group', 'RFC1918 Group'), new_only=True),
        dict(name='Block Cameras to All', action='drop', src=('net', 'cameras'), dst=('group', 'RFC1918 Group')),
        dict(name='Block All to Cameras', action='drop', src=('group', 'RFC1918 Group'), dst=('net', 'cameras')),
        dict(name='Block All to Servers', action='drop', src=('group', 'RFC1918 Group'), dst=('net', 'servers'), new_inv=True),
        dict(name='Block IoT to All Local', action='drop', src=('net', 'iot'), dst=('group', 'RFC1918 Group'), new_only=True),
    ]
    lan_local = [
        dict(name='Block plain RTSP 7447', action='reject', protocol='tcp', src=('group', 'All Home Networks'),
             dst_port_group='RTSP Unencrypted Port'),
        dict(name='Allow IoT+Servers basic gateway services', action='accept', protocol='tcp_udp',
             src=('group', 'IoT + Servers'), dst_port_group='Gateway basic services'),
        dict(name='Allow IoT+Servers ping gateway', action='accept', protocol='icmp', src=('group', 'IoT + Servers')),
        dict(name='Block IoT+Servers to gateway', action='reject', src=('group', 'IoT + Servers')),
    ]
    return dict(networks=nets, groups=groups, lan_in=lan_in, lan_local=lan_local,
                server=dict(ip=server_ip, mac=server_mac))


def print_plan(p):
    print('\nNETWORKS (VLANs)')
    for n in p['networks']:
        print(f"  VLAN {n['vlan']:<3} {n['name']:16} {n['subnet']:18} internet={'on' if n['internet'] else 'OFF'} "
              f"mDNS={'on' if n['mdns'] else 'off'}  ({n['about']})")
    print(f"\nSERVER fixed IP: {p['server']['ip']}" + (f" for {p['server']['mac']}" if p['server']['mac'] else ' (MAC chosen later)'))
    print('\nGROUPS')
    for g in p['groups']:
        print(f"  {g['name']:26} {', '.join(g['group_members'])}")
    for rs in ('lan_in', 'lan_local'):
        print(f"\n{'LAN IN' if rs == 'lan_in' else 'LAN LOCAL (traffic to the gateway itself)'} RULES, in order")
        for i, r in enumerate(p[rs], 1):
            fmt = lambda s: 'any' if not s else f'{s[0]}:{s[1]}'
            extra = (f" port {r['port']}" if r.get('port') else '') + (f" ports {r['dst_port_group']}" if r.get('dst_port_group') else '')
            st = ' (established/related)' if r.get('est') else ' (new only)' if r.get('new_only') else ''
            print(f"  {i:2}. {r['action'].upper():6} {r.get('protocol', 'all'):7} {fmt(r.get('src')):28} -> "
                  f"{fmt(r.get('dst')):28}{extra}{st}  {r['name']}")


# ─── Apply ────────────────────────────────────────────────────────────────────────────────────────────

def apply(api, p):
    existing_nets = {n['name']: n for n in api.get('rest/networkconf')}
    net_id = {}
    for n in p['networks']:
        if n['name'] in existing_nets:
            net_id[n['key']] = existing_nets[n['name']]['_id']
            print(f"  network exists, kept: {n['name']}")
            continue
        o = ipaddress.ip_interface(n['subnet'])
        hosts = list(o.network.hosts())
        body = dict(name=n['name'], purpose='corporate', networkgroup='LAN', vlan_enabled=True, vlan=n['vlan'],
                    ip_subnet=n['subnet'], dhcpd_enabled=True, dhcpd_start=str(hosts[5]), dhcpd_stop=str(hosts[-1]),
                    internet_access_enabled=n['internet'], mdns_enabled=n['mdns'], igmp_snooping=False)
        net_id[n['key']] = api.post('rest/networkconf', body)['_id']
        print(f"  created network: {n['name']}")

    existing_groups = {g['name']: g for g in api.get('rest/firewallgroup')}
    group_id = {}
    for g in p['groups']:
        if g['name'] in existing_groups:
            group_id[g['name']] = existing_groups[g['name']]['_id']
            print(f"  group exists, kept: {g['name']} (check its members match the plan)")
        else:
            group_id[g['name']] = api.post('rest/firewallgroup', g)['_id']
            print(f"  created group: {g['name']}")

    rules = api.get('rest/firewallrule')
    names = {r['name'] for r in rules}
    for rs, ruleset in (('lan_in', 'LAN_IN'), ('lan_local', 'LAN_LOCAL')):
        idx = max([r['rule_index'] for r in rules if r.get('ruleset') == ruleset and r['rule_index'] >= 20000] + [19999])
        for r in p[rs]:
            if r['name'] in names:
                print(f"  rule exists, kept: {r['name']}")
                continue
            idx += 1
            body = dict(name=r['name'], ruleset=ruleset, rule_index=idx, enabled=True, action=r['action'],
                        protocol=r.get('protocol', 'all'), protocol_match_excepted=False, logging=False,
                        setting_preference='auto', src_networkconf_type='NETv4', dst_networkconf_type='NETv4',
                        src_networkconf_id='', dst_networkconf_id='', src_firewallgroup_ids=[], dst_firewallgroup_ids=[],
                        src_address='', dst_address='', src_mac_address='', src_port='', dst_port=r.get('port', ''),
                        icmp_typename='', ipsec='', state_established=bool(r.get('est')), state_related=bool(r.get('est')),
                        state_new=bool(r.get('new_only') or r.get('new') or r.get('new_inv')),
                        state_invalid=bool(r.get('new_inv')))
            for side in ('src', 'dst'):
                s = r.get(side)
                if not s:
                    continue
                kind, val = s
                if kind == 'net':
                    body[f'{side}_networkconf_id'] = net_id[val]
                elif kind == 'group':
                    body[f'{side}_firewallgroup_ids'] = [group_id[val]]
                elif kind == 'addr':
                    body[f'{side}_address'] = val
                elif kind == 'mac':
                    body['src_mac_address'] = val
            if r.get('dst_port_group'):
                body['dst_firewallgroup_ids'] = [group_id[r['dst_port_group']]]
            api.post('rest/firewallrule', body)
            print(f"  created {ruleset} #{idx}: {r['name']}")

    if p['server']['mac']:
        users = {u['mac']: u for u in api.get('rest/user')}
        body = dict(use_fixedip=True, network_id=net_id['servers'], fixed_ip=p['server']['ip'])
        u = users.get(p['server']['mac'])
        if u:
            api.put(f"rest/user/{u['_id']}", body)
        else:
            api.post('rest/user', dict(mac=p['server']['mac'], **body))
        print(f"  server {p['server']['mac']} reserved at {p['server']['ip']} on Servers")


# ─── Main ─────────────────────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--host', help='gateway / console IP')
    ap.add_argument('--user', help='local UniFi admin username')
    ap.add_argument('--site', default='default')
    ap.add_argument('--apply', action='store_true', help='make the changes (after a typed "yes")')
    ap.add_argument('--clients-json', help='offline mode: a saved client list (JSON array) to classify')
    a = ap.parse_args()

    api = None
    if a.clients_json:
        clients = json.load(open(a.clients_json))
    else:
        if not (a.host and a.user):
            ap.error('--host and --user are required (or use --clients-json)')
        pw = os.environ.get('UNIFI_PASSWORD') or getpass.getpass(f'Password for {a.user}@{a.host} (hidden): ')
        api = UniFi(a.host, a.user, pw, a.site)
        del pw
        if api.zone_based():
            sys.exit('This console uses ZONE-BASED firewall policies. This script only writes legacy rules: '
                     'build the same layout as zone policies in the UI instead (see SKILL.md).')
        clients = api.get('stat/sta')

    print(f'\nDEVICES ON THE NETWORK ({len(clients)}), with a recommended network for each:')
    rows = show_inventory(sorted(clients, key=lambda c: (recommend(c)[0], c.get('name') or c.get('hostname') or '')))
    unknown = [c for k, c in rows if k == '?']
    if unknown:
        print(f'\n  {len(unknown)} device(s) marked "?": ask the owner what each is before moving it.')

    print('\nPlan questions (press Enter to accept the default):')
    base = ask('Address base for the networks (first two numbers)', '192.168')
    server_ip = ask('IP address for the server (on the Servers network)', f'{base}.40.10')
    servers = [c for k, c in rows if k == 'servers']
    hint = f" (suggested: {servers[0].get('name') or servers[0].get('hostname')} {servers[0]['mac']})" if servers else ''
    server_mac = ask(f'MAC address of the server, to reserve that IP{hint}; blank to skip', servers[0]['mac'] if servers else '')

    exceptions = []
    print('\nIoT devices that need to reach the server (e.g. a streaming box on IoT). Normally none.')
    iot = [c for k, c in rows if k == 'iot']
    for i, c in enumerate(iot, 1):
        print(f"  {i:2}. {(c.get('name') or c.get('hostname') or c['mac'])[:30]:30} {c['mac']}")
    picks = ask('Numbers to allow, comma-separated (blank for none)', '')
    for n in [int(x) for x in picks.replace(' ', '').split(',') if x.isdigit() and 0 < int(x) <= len(iot)]:
        c = iot[n - 1]
        label = c.get('name') or c.get('hostname') or c['mac']
        ports = ask(f"  Ports on the server for {label} (e.g. 80,443, or 8096 for Jellyfin)", '80,443')
        exceptions.append(dict(name=c.get('name') or c.get('hostname') or c['mac'], mac=c['mac'], ports=ports))

    plan = build_plan(base, server_ip, server_mac, exceptions)
    print_plan(plan)
    print('\nNot done by this script (do these in the UniFi UI):')
    print('  - Wi-Fi: create an "IoT" SSID on the IoT network (and a "Protect" SSID on Cameras if cameras use Wi-Fi).')
    print('  - Wired devices: set each switch port\'s Native VLAN to the network the device should be on.')
    print('  - Move devices to their recommended network, then reconnect them. Ubiquiti gear stays where it is.')

    if not a.apply or not api:
        print('\nDry run only: nothing was changed. Re-run with --apply to make these changes.')
        return
    if ask('\nType "yes" to create the missing networks, groups and rules above') != 'yes':
        print('Cancelled: nothing was changed.')
        return
    apply(api, plan)
    print('\nDone. Test: from an IoT device the console page should be refused, DNS should work, and the')
    print('server should be reachable from Main but not from IoT (except the devices you allowed).')


if __name__ == '__main__':
    main()
