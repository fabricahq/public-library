// Regression tests for the ratchet-files skill's check-file-size.mjs, run in
// real temporary Git repositories. Run `npm ci && npm test` in this folder.
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, renameSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { afterEach, test } from "node:test";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const script = join(
  here,
  "../../../.trailguide/skills/dzhng/ratchet-files/scripts/check-file-size.mjs",
);

// A budget of 10 tokens is 40 bytes.
const budget = ["--max-tokens", "10"];
const small = "let a = 1;\n";
const large = "let value = 1;\n".repeat(10);

const repos = [];
afterEach(() => {
  for (const repo of repos.splice(0)) rmSync(repo, { recursive: true, force: true });
});

// A repository whose package.json resolves linguist-languages from this folder.
const makeRepo = () => {
  const repo = mkdtempSync(join(tmpdir(), "ratchet-files-"));
  repos.push(repo);
  const git = (...args) => execFileSync("git", args, { cwd: repo, stdio: "pipe" });
  git("init", "-q", "-b", "main");
  git("config", "user.email", "test@example.com");
  git("config", "user.name", "Test");
  git("config", "core.quotePath", "true");
  writeFileSync(join(repo, "package.json"), "{}\n");
  symlinkSync(join(here, "node_modules"), join(repo, "node_modules"), "dir");
  writeFileSync(join(repo, ".gitignore"), "node_modules\n");
  return { repo, git, write: (path, text) => writeFileSync(join(repo, path), text) };
};

const check = (repo, ...args) => {
  const { status, stderr } = spawnSync(process.execPath, [script, ...args], {
    cwd: repo,
    encoding: "utf8",
  });
  return { status, stderr };
};

test("refuses a --max-tokens value that is not a positive whole number", () => {
  const { repo, git, write } = makeRepo();
  write("big.js", large);
  git("add", "big.js");
  for (const value of ["8k", "0", "-5", "1.5"]) {
    const { status, stderr } = check(repo, `--max-tokens=${value}`, "big.js");
    assert.equal(status, 1, `--max-tokens ${value}`);
    assert.match(stderr, /--max-tokens must be a positive whole number/);
  }
});

test("passes a small new file and refuses a new file over the budget", () => {
  const { repo, git, write } = makeRepo();
  write("small.js", small);
  write("big.js", large);
  git("add", "small.js", "big.js");
  assert.equal(check(repo, ...budget, "small.js").status, 0);
  const { status, stderr } = check(repo, ...budget, "big.js");
  assert.equal(status, 1);
  assert.match(stderr, /big\.js: .*a new file/);
});

test("holds a file already over the budget to its HEAD size", () => {
  const { repo, git, write } = makeRepo();
  write("big.js", large);
  git("add", "big.js");
  git("commit", "-q", "-m", "base");
  write("big.js", `${large}let more = 2;\n`);
  git("add", "big.js");
  const { status, stderr } = check(repo, ...budget, "big.js");
  assert.equal(status, 1);
  assert.match(stderr, /already over the budget/);
});

test("measures a staged rename of a non-ASCII path against the file it came from", () => {
  const { repo, git, write } = makeRepo();
  write("ancien é.js", large);
  git("add", "ancien é.js");
  git("commit", "-q", "-m", "base");
  renameSync(join(repo, "ancien é.js"), join(repo, "nouveau é.js"));
  git("add", "-A");
  const { status, stderr } = check(repo, ...budget, "nouveau é.js");
  assert.equal(status, 0, stderr);
});
