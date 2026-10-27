// Sends JSON messages (one per argument) over Home Assistant's WebSocket API and prints each result.
// Usage: HA_HOST=192.168.x.x:8123 HA_TOKEN=... node ha-ws.mjs '{"type":"config/entity_registry/list"}'
// Many messages: write them NUL-separated to a file, then: xargs -0 env HA_TOKEN=$HA_TOKEN node ha-ws.mjs < msgs
const host = process.env.HA_HOST ?? 'homeassistant.local:8123';
const msgs = process.argv.slice(2).map(m => JSON.parse(m));
const ws = new WebSocket(`ws://${host}/api/websocket`);
let id = 0;
ws.onmessage = ({ data }) => {
  const m = JSON.parse(data);
  if (m.type === 'auth_required') return ws.send(JSON.stringify({ type: 'auth', access_token: process.env.HA_TOKEN }));
  if (m.type === 'auth_invalid') { console.error('auth failed: check HA_TOKEN'); process.exit(1); }
  if (m.type === 'auth_ok' || m.type === 'result') {
    if (m.type === 'result') console.log(JSON.stringify(m.success ? m.result : { error: m.error }));
    if (id < msgs.length) ws.send(JSON.stringify({ id: ++id, ...msgs[id - 1] })); else ws.close();
  }
};
