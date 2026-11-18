const { test } = require("node:test");
const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

test("standalone canvas restores prototype work until the renamed key exists", async (t) => {
  const root = path.resolve(__dirname, "../..");
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "grill-upgrade-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const output = path.join(dir, "canvas.html");
  const snapshot = {
    id: "upgrade", revision: 1, title: "Release planning",
    nodes: [
      { id: "Q1", parentId: null, title: "Rollout", question: "Who goes first?", answer: null },
      { id: "Q2", parentId: null, title: "Timing", question: "When do we start?", answer: null },
    ],
  };
  const input = path.join(dir, "input.json");
  fs.writeFileSync(input, JSON.stringify(snapshot));
  execFileSync("python3", [path.join(root, "scripts/grill_ui.py"), "render",
    "--snapshot", input, "--output", output]);
  const browser = await chromium.launch();
  t.after(() => browser.close());
  const page = await browser.newPage();
  page.setDefaultTimeout(3000);
  await page.goto(pathToFileURL(output).href);
  const draft = page.locator("#draft");
  const open = (id) => page.locator('[data-node="' + id + '"]').click();
  const close = () => page.locator("#closePanel").click();

  await open("Q1");
  await draft.fill("Invite existing customers");
  await page.locator("#send").click();
  await page.locator(".answer-body").filter({ hasText: "Invite existing customers" }).waitFor();
  await close();
  await open("Q2");
  await draft.fill("Next Tuesday");

  // The prototype wrote the same payload under its original session key.
  await page.evaluate(() => {
    const saved = localStorage.getItem("grill-me-ui:upgrade");
    if (!saved) throw Error("Missing saved session");
    localStorage.setItem("grill-ui:upgrade", saved);
    localStorage.removeItem("grill-me-ui:upgrade");
  });
  await page.reload();
  await open("Q1");
  await page.locator(".answer-body").filter({ hasText: "Invite existing customers" }).waitFor();
  await close();
  await open("Q2");
  assert.equal(await draft.inputValue(), "Next Tuesday");
  await draft.fill("Next Wednesday");
  await page.reload();
  await open("Q2");
  assert.equal(await draft.inputValue(), "Next Wednesday");
});
