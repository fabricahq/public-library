const { chromium } = require("playwright");
const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs"),
  os = require("node:os"),
  path = require("node:path"),
  assert = require("node:assert/strict");
const root = path.resolve(__dirname, "../.."),
  script = path.join(root, "scripts/grill_ui.py");
(async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "grill-focus-"));
  let server, browser;
  const cli = (...args) => {
    const result = spawnSync("python3", [script, ...args], {
      encoding: "utf8",
    });
    assert.equal(result.status, 0, result.stderr + result.stdout);
    return JSON.parse(result.stdout);
  };
  try {
    cli(
      "publish",
      "--session-dir",
      dir,
      "--snapshot",
      path.join(root, "examples/design-context.json"),
      "--expected-revision",
      "0",
    );
    const file = path.join(dir, "focus.md");
    fs.writeFileSync(
      file,
      "# Focus audit\n\n## Section one\n\nDocument text.\n\n## Section two\n\nMore text.",
    );
    cli(
      "artifact",
      "--session-dir",
      dir,
      "--file",
      file,
      "--title",
      "Focus document",
    );
    server = spawn("python3", [script, "serve", "--session-dir", dir]);
    const url = await new Promise((resolve, reject) => {
      let out = "";
      server.stdout.on("data", (chunk) => {
        out += chunk;
        if (out.includes("\n")) resolve(JSON.parse(out.split("\n")[0]).url);
      });
      server.on("exit", (code) => reject(Error("Server exited " + code)));
    });
    browser = await chromium.launch({
      headless: true,
      executablePath: process.env.CHROMIUM_EXECUTABLE_PATH,
    });
    const page = await browser.newPage({
      viewport: { width: 1440, height: 950 },
    });
    page.setDefaultTimeout(5000);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const ring = (locator) =>
      locator.evaluate((el) => {
        const style = getComputedStyle(el);
        return (
          style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0
        );
      });
    const clickQuiet = async (locator) => {
      await locator.click();
      assert.equal(
        await ring(locator),
        false,
        "Mouse click must not draw a keyboard ring",
      );
    };
    const keyboardFocus = async (locator) => {
      await page.keyboard.press("Tab");
      await locator.focus();
      assert(await ring(locator), "Keyboard focus must remain visible");
    };
    await page.goto(url);
    const trigger = page.locator("#confidenceGroups");
    await clickQuiet(trigger);
    assert.equal(
      await ring(page.locator("#confidenceGroupMenu [data-pair]").first()),
      false,
    );
    await clickQuiet(page.locator("#includeUnassessed"));
    await clickQuiet(page.locator("#finishConfidenceGroups"));
    assert.equal(await ring(trigger), false);
    await keyboardFocus(trigger);
    await page.keyboard.press("Enter");
    assert.equal(
      await ring(trigger),
      false,
      "Open menu must not retain a second focus ring on its trigger",
    );
    assert(
      await ring(page.locator("#confidenceGroupMenu [data-pair]").first()),
    );
    await page.keyboard.press("Escape");
    assert(await ring(trigger));
    await clickQuiet(trigger);
    await keyboardFocus(page.locator("#includeUnassessed"));
    await clickQuiet(page.locator("#includeUnassessed"));
    await clickQuiet(page.locator("#finishConfidenceGroups"));
    await clickQuiet(page.locator("#menuButton"));
    const appearance = page.locator("#appearance");
    const dismissAppearancePicker = async () => {
      // selectOption does not close Chromium's native popup on Linux. Escape
      // dismisses it; on macOS it may instead close the surrounding app menu.
      await page.keyboard.press("Escape");
      if (!(await page.locator("#menu").isVisible())) {
        await page.locator("#menuButton").click();
      }
    };
    await clickQuiet(appearance);
    await appearance.selectOption("light");
    await dismissAppearancePicker();
    // Tab into Appearance from the preceding canvas control, as a user would.
    await page.locator("#zoomIn").focus();
    await page.keyboard.press("Tab");
    assert(await appearance.evaluate(el => document.activeElement === el));
    assert(await ring(appearance), "Tab must draw a focus ring on Appearance");
    await clickQuiet(appearance);
    await appearance.selectOption("system");
    await dismissAppearancePicker();
    await clickQuiet(page.locator("#openAbout"));
    const link = page.locator("#aboutDialog a").first();
    await keyboardFocus(link);
    // Prevent external navigation while exercising an actual pointer click on the focused link.
    await link.evaluate((el) =>
      el.addEventListener("click", (event) => event.preventDefault(), {
        once: true,
      }),
    );
    await clickQuiet(link);
    await clickQuiet(page.locator("#closeAbout"));
    await clickQuiet(page.locator("#artifactsButton"));
    await page
      .getByRole("button", { name: "Open focus.md on canvas", exact: true })
      .click();
    await clickQuiet(page.locator("#closeArtifacts"));
    const win = page.locator(".artifact-window");
    await clickQuiet(
      win.getByRole("button", { name: "Zoom in document", exact: true }),
    );
    await clickQuiet(win.locator(".artifact-maximize"));
    await clickQuiet(win.getByRole("button", { name: "Source", exact: true }));
    await clickQuiet(
      win.getByRole("button", { name: "Rendered", exact: true }),
    );
    await clickQuiet(
      win.getByRole("button", { name: "Section two", exact: true }),
    );
    const restore = win.locator(".artifact-maximize");
    await keyboardFocus(restore);
    await clickQuiet(restore);
    assert.deepEqual(errors, []);
    console.log(
      "PASS pointer and keyboard focus for filter, checkboxes, appearance, links, dialogs, and document controls",
    );
  } finally {
    await browser?.close();
    server?.kill();
    fs.rmSync(dir, { recursive: true, force: true });
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
