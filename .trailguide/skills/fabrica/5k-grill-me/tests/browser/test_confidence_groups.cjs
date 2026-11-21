const { chromium } = require("playwright");
const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs"),
  os = require("node:os"),
  path = require("node:path"),
  assert = require("node:assert/strict");
const script = path.resolve(__dirname, "../../scripts/grill_ui.py");
(async () => {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "grill-confidence-groups-"),
  );
  let server, browser;
  const levels = ["low", "medium", "high"];
  const assessment = (level) => ({ level, reason: "Test assessment." });
  const nodes = levels.flatMap((context, c) =>
    levels.map((advice, a) => ({
      id: `Q${c}${a}`,
      parentId: null,
      title: `${context} / ${advice}`,
      question: "Which direction should we choose?",
      answer: null,
      dependsOn: [],
      agentRecommendationSummary: "An example direction.",
      contextConfidence: assessment(context),
      recommendationConfidence: assessment(advice),
    })),
  );
  nodes.push({
    id: "unknown",
    parentId: null,
    title: "Not assessed",
    question: "What is intended?",
    answer: null,
    dependsOn: [],
  });
  nodes.push({
    id: "no-advice",
    parentId: null,
    title: "No recommendation",
    question: "What next?",
    answer: null,
    dependsOn: [],
    contextConfidence: assessment("low"),
    recommendationConfidence: assessment("low"),
  });
  const snapshot = {
    id: "confidence-groups-test",
    schemaVersion: 1,
    title: "Confidence groups test",
    revision: 1,
    nodes,
  };
  const file = path.join(dir, "snapshot.json");
  fs.writeFileSync(file, JSON.stringify(snapshot));
  try {
    const pub = spawnSync(
      "python3",
      [
        script,
        "publish",
        "--session-dir",
        dir,
        "--snapshot",
        file,
        "--expected-revision",
        "0",
      ],
      { encoding: "utf8" },
    );
    assert.equal(pub.status, 0, pub.stderr + pub.stdout);
    server = spawn("python3", [script, "serve", "--session-dir", dir]);
    const url = await new Promise((resolve, reject) => {
      let out = "";
      server.stdout.on("data", (c) => {
        out += c;
        if (out.includes("\n")) resolve(JSON.parse(out.split("\n")[0]).url);
      });
      server.on("exit", (code) => reject(Error("Server exited " + code)));
    });
    browser = await chromium.launch({
      headless: true,
      executablePath: process.env.CHROMIUM_EXECUTABLE_PATH,
    });
    const page = await browser.newPage({
      viewport: { width: 1500, height: 1000 },
    });
    page.setDefaultTimeout(7000);
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(url);
    await page.locator("#matrixView").click();
    const ids = async () =>
      (
        await page
          .locator(".matrix-decision")
          .evaluateAll((els) => els.map((el) => el.dataset.confidenceNode))
      ).sort();
    const picker = page.locator("#confidenceGroupMenu");
    const open = async () => {
      if (!(await picker.isVisible()))
        await page.locator("#confidenceGroups").click();
    };
    const cell = (c, a) => picker.locator(`[data-pair="${c},${a}"]`);
    const titled = ["Low", "Medium", "High"];
    await open();
    await page.locator("#noConfidenceGroups").click();
    assert.deepEqual(await ids(), []);
    for (const [c, context] of titled.entries()) {
      for (const [a, advice] of titled.entries()) {
        await cell(context, advice).click();
        assert.deepEqual(await ids(), [`Q${c}${a}`]);
        assert.equal(
          await cell(context, advice).getAttribute("aria-checked"),
          "true",
        );
        await cell(context, advice).click();
        assert.deepEqual(await ids(), []);
      }
    }
    await cell("Low", "Low").focus();
    await page.keyboard.press("Space");
    assert.deepEqual(await ids(), ["Q00"]);
    await page.keyboard.press("Space");
    assert.deepEqual(await ids(), []);
    await cell("Low", "High").click();
    await cell("High", "Low").click();
    assert.deepEqual(await ids(), ["Q02", "Q20"]);
    await page.keyboard.press("Escape");
    assert(
      await page
        .locator("#confidenceGroups")
        .evaluate((el) => el === document.activeElement),
    );
    assert(!(await picker.isVisible()));
    await page.locator('[data-confidence-node="Q02"]').click();
    await page.locator("#customTab").click();
    await page.locator("#draft").fill("Keep this draft.");
    await page.locator("#treeView").click();
    assert.equal(
      await page.locator("#tree foreignObject.confidence-muted").count(),
      nodes.length - 2,
    );
    await page.locator("#matrixView").click();
    assert.deepEqual(await ids(), ["Q02", "Q20"]);
    await open();
    await cell("Low", "High").click();
    assert.deepEqual(await ids(), ["Q20"]);
    await page.locator("#includeUnassessed").check();
    assert.deepEqual(await ids(), ["Q20", "no-advice", "unknown"]);
    await page.locator("#includeUnassessed").uncheck();
    await cell("Low", "Low").click();
    await page.locator("#finishConfidenceGroups").click();
    assert.deepEqual(await ids(), ["Q00", "Q20"]);
    assert.equal(
      await page
        .locator("#contextConfidence, #adviceConfidence, #confidenceLevelMenu")
        .count(),
      0,
    );
    assert.equal(
      await page.locator("#confidenceGroups .filter-active").textContent(),
      "On",
    );
    assert.equal(
      await page.locator("#confidenceCount strong").textContent(),
      "2",
    );
    assert.equal(
      await cell("Low", "Low").locator(".group-clarification").textContent(),
      "Most to clarify",
    );
    assert.equal(await page.locator("#draft").inputValue(), "Keep this draft.");
    await page.locator("#resetConfidence").click();
    assert.equal((await ids()).length, nodes.length);
    assert(await page.locator("#resetConfidence").isDisabled());
    await open();
    await page.locator("#noConfidenceGroups").click();
    await page.locator("#finishConfidenceGroups").click();
    assert(await page.locator("#nextQuestion").isDisabled());
    await page.locator("#jumpUncertain").click();
    assert.deepEqual(await ids(), ["Q00"]);
    await page
      .getByRole("button", { name: "Clear focus", exact: true })
      .click();
    assert.equal((await ids()).length, nodes.length);
    await open();
    await page.locator("#noConfidenceGroups").click();
    await page.locator("#allConfidenceGroups").click();
    assert.equal((await ids()).length, nodes.length);
    await page.locator("#matrixView").click();
    assert(!(await picker.isVisible()));
    await open();
    await page.locator("#closeConfidenceGroups").click();
    assert(!(await picker.isVisible()));
    await page.setViewportSize({ width: 390, height: 844 });
    await open();
    assert(
      await picker.evaluate((el) => {
        const r = el.getBoundingClientRect();
        return (
          r.left >= 0 &&
          r.right <= innerWidth &&
          r.top >= 0 &&
          r.bottom <= innerHeight
        );
      }),
    );
    await cell("Low", "Low").click();
    assert.equal(
      await cell("Low", "Low").getAttribute("aria-checked"),
      "false",
    );
    await page.locator("#finishConfidenceGroups").click();
    await page.locator("#resetConfidence").click();
    assert.equal((await ids()).length, nodes.length);
    assert.deepEqual(errors, []);
    console.log(
      "PASS nine independent pairs, arbitrary combinations, unassessed, both views, drafts, live result count and single filter state, focus/reset, keyboard/dismissal, and mobile picker",
    );
  } finally {
    await browser?.close();
    server?.kill();
    fs.rmSync(dir, { recursive: true, force: true });
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
