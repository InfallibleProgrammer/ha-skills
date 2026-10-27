// Pushes the dashboards in dashboard.mjs to Home Assistant over its WebSocket API.
// Usage: HA_HOST=<HA_IP>:8123 HA_TOKEN=... CARD_V=<n> node deploy.mjs   (copy home-dash.js to /config/www first)
import { dashboards } from './dashboard.mjs';   // e.g. [{ url_path: 'home-dash', title: 'Home', icon: 'mdi:home', config }]

const HOST = process.env.HA_HOST ?? 'homeassistant.local:8123';
const RESOURCE = `/local/home-dash.js?v=${process.env.CARD_V ?? '1'}`;

const ws = new WebSocket(`ws://${HOST}/api/websocket`);
let nextId = 1;
const pending = new Map();
const send = msg => new Promise((resolve, reject) => {
  const id = nextId++;
  pending.set(id, { resolve, reject });
  ws.send(JSON.stringify({ id, ...msg }));
});

ws.onmessage = ({ data }) => {
  const msg = JSON.parse(data);
  if (msg.type === 'auth_required') return ws.send(JSON.stringify({ type: 'auth', access_token: process.env.HA_TOKEN }));
  if (msg.type === 'auth_invalid') { console.error('auth failed'); process.exit(1); }
  if (msg.type === 'auth_ok') return run().then(() => ws.close(), e => { console.error(e); process.exit(1); });
  const p = pending.get(msg.id);
  if (!p) return;
  pending.delete(msg.id);
  msg.success ? p.resolve(msg.result) : p.reject(new Error(JSON.stringify(msg.error)));
};

async function run() {
  // Point the card resource at the current version (adds it the first time).
  const resources = await send({ type: 'lovelace/resources' });
  const existing = resources.find(r => r.url.startsWith('/local/home-dash.js'));
  if (!existing) await send({ type: 'lovelace/resources/create', res_type: 'module', url: RESOURCE });
  else if (existing.url !== RESOURCE) await send({ type: 'lovelace/resources/update', resource_id: existing.id, res_type: 'module', url: RESOURCE });
  console.log('resource:', RESOURCE);

  const have = await send({ type: 'lovelace/dashboards/list' });
  for (const d of dashboards) {
    if (!have.some(h => h.url_path === d.url_path)) {
      await send({ type: 'lovelace/dashboards/create', url_path: d.url_path, title: d.title, icon: d.icon,
        show_in_sidebar: true, require_admin: d.require_admin ?? false, mode: 'storage' });
      console.log('created /' + d.url_path);
    }
    await send({ type: 'lovelace/config/save', url_path: d.url_path, config: d.config });
    console.log(`saved ${d.title}:`, d.config.views.map(v => v.title).join(', '));
  }
}
