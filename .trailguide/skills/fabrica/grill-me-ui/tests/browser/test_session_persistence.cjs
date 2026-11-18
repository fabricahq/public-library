const {test} = require("node:test");
const assert = require("node:assert/strict");
const {execFileSync, spawn} = require("node:child_process");
const {once} = require("node:events");
const {createInterface} = require("node:readline");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {pathToFileURL} = require("node:url");
const {chromium} = require("playwright");
const script = path.resolve(__dirname, "../../scripts/grill_ui.py");

async function setup(t, ids) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "grill-persist-"));
  t.after(() => fs.rmSync(dir, {recursive:true, force:true}));
  const input = path.join(dir, "input.json");
  const nodes = ids.map(id => ({id, parentId:null, title:id, question:"How should we proceed?", answer:null}));
  fs.writeFileSync(input, JSON.stringify({id:"persist", title:"Project", revision:1, nodes}));
  const browser = await chromium.launch();
  t.after(() => browser.close());
  const context = await browser.newContext();
  async function pageAt(url) {
    const page = await context.newPage();
    page.setDefaultTimeout(3000);
    await page.goto(url);
    return page;
  }
  const file = path.join(dir,"canvas.html");
  execFileSync("python3", [script,"render","--snapshot",input,"--output",file]);
  return {pageAt, url:pathToFileURL(file).href, dir, input};
}
const open = (page,id) => page.locator('[data-node="'+id+'"]').click();
async function answer(page,text) {
  await page.locator("#draft").fill(text);
  await page.locator("#send").click();
}

test("a stale standalone tab keeps the newer answer and its own draft", async t => {
  const {pageAt,url} = await setup(t,["Q1","Q2"]);
  const first = await pageAt(url), second = await pageAt(url);
  await open(first,"Q1"); await open(second,"Q2");
  await answer(first,"First answer");
  await first.locator(".answer-body").filter({hasText:"First answer"}).waitFor();
  await answer(second,"Second draft");
  await first.reload(); await open(first,"Q1");
  await first.locator(".answer-body").filter({hasText:"First answer"}).waitFor();
  assert.equal(await second.locator("#draft").inputValue(),"Second draft");
  await second.reload(); await open(second,"Q2");
  assert.equal(await second.locator("#draft").inputValue(),"Second draft");
  await second.locator("#send").click();
  await second.locator(".answer-body").filter({hasText:"Second draft"}).waitFor();
});

test("valid question IDs can use ordinary object property names", async t => {
  const {pageAt,url} = await setup(t,["constructor","__proto__"]);
  const page = await pageAt(url);
  for (const id of ["constructor","__proto__"]) {
    await open(page,id); await answer(page,id+" answer");
    await page.locator(".answer-body").filter({hasText:id+" answer"}).waitFor();
    await page.reload();
  }
});

test("resume with port zero restores the unfinished live draft", async t => {
  const {pageAt,dir,input} = await setup(t,["Q1"]);
  execFileSync("python3",[script,"publish","--session-dir",dir,"--snapshot",input,"--expected-revision","0"]);
  let server;
  async function start() {
    server = spawn("python3",[script,"serve","--session-dir",dir,"--port","0"]);
    const lines = createInterface({input:server.stdout});
    for await (const line of lines) return JSON.parse(line).url;
    throw Error("No server URL");
  }
  t.after(() => server?.kill());
  const page = await pageAt(await start());
  await open(page,"Q1"); await page.locator("#draft").fill("Work in progress");
  const stopped = once(server,"exit"); server.kill(); await stopped;
  await page.goto(await start());
  await open(page,"Q1");
  assert.equal(await page.locator("#draft").inputValue(),"Work in progress");
});
