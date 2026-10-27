// Opens a Home Assistant dashboard in headless Chrome, logged in with HA_TOKEN, prints error cards and
// console errors, and saves a screenshot.
// Usage: HA_TOKEN=... node ha-screenshot.mjs http://<HA_IP>:8123/<dashboard>/<view> out.png /tmp/chrome-profile
// CHROME can point at the Chrome binary (default: the macOS path).
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
const [, , url, shot = 'dashboard.png', profile = '/tmp/ha-chrome-profile'] = process.argv;
const bin = process.env.CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const chrome = spawn(bin, ['--headless=new', '--remote-debugging-port=9333', `--user-data-dir=${profile}`,
  '--window-size=900,2400', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
await sleep(1500);
const targets = await (await fetch('http://127.0.0.1:9333/json')).json();
const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
await new Promise(r => (ws.onopen = r));
let id = 0; const pend = new Map(); const logs = [];
ws.onmessage = ({ data }) => {
  const m = JSON.parse(data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result); pend.delete(m.id); }
  if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type))
    logs.push(m.params.type + ': ' + m.params.args.map(a => a.value ?? a.description).join(' '));
  if (m.method === 'Runtime.exceptionThrown')
    logs.push('exception: ' + (m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text));
};
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send('Runtime.enable');
const origin = new URL(url).origin;
// Log in by planting the token where the frontend looks for it.
await send('Page.navigate', { url: origin + '/onboarding.html' }); await sleep(1500);
const tokens = JSON.stringify({ access_token: process.env.HA_TOKEN, token_type: 'Bearer', expires_in: 1e9, hassUrl: origin,
  clientId: origin + '/', expires: Date.now() + 1e12, refresh_token: '' });
await send('Runtime.evaluate', { expression: `localStorage.setItem('hassTokens', ${JSON.stringify(tokens)})` });
await send('Page.navigate', { url }); await sleep(12000);
// Walk every shadow root looking for error or warning cards.
const r = await send('Runtime.evaluate', { returnByValue: true, expression: `(() => {
  const out = []; const walk = n => { if (!n) return;
    if (n.tagName && /HUI-ERROR-CARD|HUI-WARNING/.test(n.tagName)) out.push(n.tagName + ': ' + (n.shadowRoot?.textContent || n.textContent).trim().replace(/\\s+/g, ' ').slice(0, 400));
    n.shadowRoot && [...n.shadowRoot.children].forEach(walk); [...(n.children || [])].forEach(walk); };
  walk(document.body); return out; })()` });
console.log('ERROR CARDS:', JSON.stringify(r.result.value, null, 1));
console.log('CONSOLE:', logs.slice(0, 20).join('\n'));
const s = await send('Page.captureScreenshot', { format: 'png' });
writeFileSync(shot, Buffer.from(s.data, 'base64'));
chrome.kill(); process.exit(0);
