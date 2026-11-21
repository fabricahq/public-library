// Walks every state of the given components in a built preview page, several pages at once, and screenshots
// each component's first state in both themes, clipped to what it draws. Serves the folder to the browser
// through Playwright's routing, so no server listens.
// Usage: node walk.cjs <built preview dir> <states.json> <thumbs dir> [concurrency]
//   states.json: {"Component": ["state-id", ...], ...}; a component listed as "Part@Card" is walked as Part,
//   and the card it belongs to gets no thumbnail of it.
// Prints JSON: {"Component": {"size": [w, h], "states": {"id": {"errors": [...], "text": "..."}}}}
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const [dir, statesFile, thumbs, conc = '6'] = process.argv.slice(2);
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json', '.mp4': 'video/mp4', '.woff2': 'font/woff2' };
const root = path.resolve(dir);
const serve = (ctx) => ctx.route('http://preview.local/**', (r) => {
  let p = decodeURIComponent(new URL(r.request().url()).pathname); if (p.endsWith('/')) p += 'index.html';
  const f = path.join(root, p);
  if (!f.startsWith(root) || !fs.existsSync(f)) return r.fulfill({ status: 404, body: 'not found' });
  r.fulfill({ status: 200, contentType: TYPES[path.extname(f)] || 'application/octet-stream', body: fs.readFileSync(f) });
});
const url = (c, s, theme) => `http://preview.local/index.html?c=${encodeURIComponent(c)}&s=${encodeURIComponent(s)}&shot=1&theme=${theme}`;

(async () => {
  const want = JSON.parse(fs.readFileSync(statesFile, 'utf8'));
  fs.mkdirSync(thumbs, { recursive: true });
  const jobs = [];
  for (const [key, ids] of Object.entries(want)) {
    const comp = key.split('@')[0], part = key.includes('@');
    ids.forEach((id) => jobs.push({ key, comp, id, kind: 'state' }));
    if (!part && ids.length) for (const theme of ['light', 'dark']) jobs.push({ key, comp, id: ids[0], kind: 'thumb', theme });
  }
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1200, height: 900 } }); await serve(ctx);
  const out = {};
  const worker = async () => {
    const p = await ctx.newPage(); const errs = [];
    p.on('pageerror', (e) => errs.push(e.message.slice(0, 200)));
    p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)); });
    for (let job; (job = jobs.shift());) {
      errs.length = 0;
      await p.goto(url(job.comp, job.id, job.theme || 'light')); await p.waitForTimeout(900);
      const o = (out[job.key] ??= { states: {} });
      if (job.kind === 'state') {
        o.states[job.id] = { errors: [...errs], text: (await p.innerText('body')).trim().replace(/\s+/g, ' ').slice(0, 80) };
        continue;
      }
      // What the component draws: the union of its boxes, plus a margin. Boxes as wide as the page are the
      // preview's own wrappers, not the component.
      const box = await p.evaluate(() => {
        let r = 0, bt = 0;
        for (const el of document.body.querySelectorAll('*')) { const q = el.getBoundingClientRect(); if (q.width && q.height && q.width < innerWidth - 1 && getComputedStyle(el).visibility !== 'hidden') { r = Math.max(r, q.right); bt = Math.max(bt, q.bottom); } }
        return [Math.min(1200, Math.ceil(r + 16)), Math.ceil(Math.max(bt + 16, 60))];
      });
      if (job.theme === 'light') o.size = box;
      await p.screenshot({ path: path.join(thumbs, `${job.comp}-${job.theme}.png`), clip: { x: 0, y: 0, width: box[0], height: box[1] }, fullPage: box[1] > 900 });
    }
    await p.close();
  };
  await Promise.all(Array.from({ length: Math.max(1, +conc) }, worker));
  await b.close();
  console.log(JSON.stringify(out, null, 1));
})();
