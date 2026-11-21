#!/usr/bin/env python3
"""The mechanical half of a 5K PR review scan, so a rescan redoes only what changed and the agent's own time goes to
writing about it. Each subcommand prints JSON; the agent turns it into the snapshot's prose.

  changes   What changed between base and head, by kind, and with --since the last scanned head, which
            steps a rescan must redo. Also how recently the branch moved, to tell whether it has settled.
  checkout  Make or move a scratch worktree to a commit, installing JavaScript dependencies only when the
            lockfile changed since the tree's last install.
  schema    Apply the migrations at base and head to fresh Postgres databases, read straight from git, dump
            both schemas and diff them by table, column, constraint, index and policy.
  stats     Files, lines, commits, and the lines in tests and generated files.
  components  The frontend components the PR adds or changes, each with the PR's components it draws (by JSX
            use, its file's own helpers included), those that draw it, and its level from the bottom up.
  deadcode  Run knip (and, for Go, deadcode and staticcheck) in two checked-out trees and diff the findings.

Postgres is reached with the command in PR_REVIEW_PSQL (default `psql`) and PR_REVIEW_PG_DUMP (default `pg_dump`),
for example `runuser -u postgres -- psql`.
"""
import argparse, fnmatch, hashlib, json, os, re, shlex, subprocess, sys, time
from pathlib import Path


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=check).stdout


def changed(repo, a, b):
    return [l for l in git(repo, "diff", "--name-only", f"{a}..{b}").splitlines() if l]


KINDS = [
    ("migration", lambda f, o: fnmatch.fnmatch(f, o.migrations)),
    ("catalog", lambda f, o: ".catalog." in f or (o.catalog and f.startswith(o.catalog.rstrip("/") + "/"))),
    ("generated", lambda f, o: re.search(o.generated, f) is not None),
    ("test", lambda f, o: re.search(r"(_test\.go|\.test\.[jt]sx?|\.spec\.[jt]sx?)$", f) is not None),
    ("go", lambda f, o: f.endswith(".go")),
    ("component", lambda f, o: f.endswith(".tsx")),
    ("ts", lambda f, o: re.search(r"\.[cm]?[jt]sx?$", f) is not None),
    ("lockfile", lambda f, o: Path(f).name in LOCKFILES),
    ("docs", lambda f, o: f.endswith(".md")),
]
LOCKFILES = {"bun.lock", "bun.lockb", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}


def classify(files, o):
    out = {}
    for f in files:
        kind = next((k for k, test in KINDS if test(f, o)), "other")
        out.setdefault(kind, []).append(f)
    return out


def cmd_changes(o):
    files = changed(o.repo, o.base, o.head)
    res = {"base": o.base, "head": git(o.repo, "rev-parse", "--short", o.head).strip(), "byKind": {k: len(v) for k, v in classify(files, o).items()}}
    # How recently the branch moved: a head pushed minutes ago, in a run of pushes, is likely to move again.
    now = time.time()
    stamps = [int(t) for t in git(o.repo, "log", "--format=%ct", "-20", f"{o.base}..{o.head}").split()]
    res["headAgeMinutes"] = round((now - stamps[0]) / 60, 1) if stamps else None
    res["commitsInLast15Minutes"] = sum(1 for t in stamps if now - t < 900)
    if o.since:
        delta = changed(o.repo, o.since, o.head)
        kinds = classify(delta, o)
        res["since"] = o.since
        res["sinceCommits"] = git(o.repo, "log", "--format=%h %s", f"{o.since}..{o.head}").splitlines()
        res["sinceByKind"] = kinds
        has = lambda *k: any(kinds.get(x) for x in k)
        res["redo"] = {
            "schema": has("migration"),
            "backend": has("go"),
            "goDeadcode": has("go"),
            "frontend": has("component", "ts"),
            "props": sorted(f for f in kinds.get("component", []) if ".catalog." not in f),
            "catalog": has("catalog", "component", "lockfile"),
            "knip": has("component", "ts", "lockfile"),
            "install": has("lockfile"),
            "evidence": has("test"),
            "stats": bool(delta),
        }
    print(json.dumps(res, indent=1))


def lock_digest(tree):
    for name in sorted(LOCKFILES):
        p = Path(tree) / name
        if p.exists():
            return name, hashlib.sha256(p.read_bytes()).hexdigest()
    return None, None


def cmd_checkout(o):
    tree = Path(o.dir)
    if not tree.exists():
        git(o.repo, "worktree", "add", "--detach", str(tree), o.ref)
    else:
        subprocess.run(["git", "-C", str(tree), "checkout", "-q", "--detach", o.ref], check=True)
    name, digest = lock_digest(tree)
    stamp = tree / ".5k-pr-review-installed"
    installed = False
    if name and (not stamp.exists() or stamp.read_text() != digest) and not o.no_install:
        tool = {"bun.lock": ["bun", "install", "--frozen-lockfile"], "bun.lockb": ["bun", "install", "--frozen-lockfile"],
                "package-lock.json": ["npm", "ci"], "pnpm-lock.yaml": ["pnpm", "install", "--frozen-lockfile"],
                "yarn.lock": ["yarn", "install", "--frozen-lockfile"]}[name]
        subprocess.run(tool, cwd=tree, check=True, capture_output=True)
        stamp.write_text(digest)
        installed = True
    print(json.dumps({"tree": str(tree), "ref": git(str(tree), "rev-parse", "--short", "HEAD").strip(), "installed": installed}))


# ---- schema ---------------------------------------------------------------------------------------------

def migration_sql(text, fmt):
    if fmt == "goose":
        up = text.split("-- +goose Down")[0]
        return "\n".join(l for l in up.splitlines() if not l.startswith("-- +goose"))
    return text


def run_psql(args, sql=None):
    cmd = shlex.split(os.environ.get("PR_REVIEW_PSQL", "psql")) + ["-q", "-v", "ON_ERROR_STOP=1", *args]
    r = subprocess.run(cmd, input=sql, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"psql failed: {r.stderr.strip()[:2000]}")
    return r.stdout


def build_db(o, ref, name):
    run_psql(["-d", "postgres", "-c", f'DROP DATABASE IF EXISTS "{name}"'])
    run_psql(["-d", "postgres", "-c", f'CREATE DATABASE "{name}"'])
    if o.setup:
        run_psql(["-d", name], Path(o.setup).read_text())
    files = sorted(f for f in git(o.repo, "ls-tree", "-r", "--name-only", ref).splitlines() if fnmatch.fnmatch(f, o.migrations))
    for f in files:
        try:
            run_psql(["-d", name], migration_sql(git(o.repo, "show", f"{ref}:{f}"), o.format))
        except SystemExit as e:
            raise SystemExit(f"{ref}:{f}: {e}")
    dump = subprocess.run(shlex.split(os.environ.get("PR_REVIEW_PG_DUMP", "pg_dump")) + ["-s", "-O", "-x", "-d", name], capture_output=True, text=True, check=True).stdout
    return files, dump


def parse_functions(dump):
    """Each function's signature and body, from pg_dump -s output."""
    out = {}
    for m in re.finditer(r"CREATE FUNCTION ([\w.\"]+)\((.*?)\) RETURNS (.*?)\n(.*?)\$(\w*)\$(.*?)\$\5\$", dump, re.S):
        out[f"{m.group(1).replace('public.', '')}({m.group(2)})"] = re.sub(r"\s+", " ", f"returns {m.group(3)} {m.group(4)} {m.group(6)}").strip()
    return out


def parse_dump(dump):
    """Tables with their columns, constraints, indexes and policies, from pg_dump -s output."""
    tables = {}
    body = "\n".join(l for l in dump.splitlines() if not l.startswith("--"))
    for st in re.split(r";\s*\n", body):
        st = st.strip()
        m = re.match(r"CREATE TABLE (?:ONLY )?([\w.\"]+) \((.*)\)\s*$", st, re.S)
        if m:
            t = tables.setdefault(m.group(1).replace("public.", "").strip('"'), {"columns": {}, "constraints": {}, "indexes": {}, "policies": {}, "rls": False})
            for line in re.split(r",\n", m.group(2)):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("CONSTRAINT "):
                    n, d = line[11:].split(" ", 1); t["constraints"][n.strip('"')] = d
                    continue
                cm = re.match(r'("?[\w]+"?) (.+)$', line, re.S)
                if cm:
                    t["columns"][cm.group(1).strip('"')] = re.sub(r"\s+", " ", cm.group(2))
            continue
        m = re.match(r"ALTER TABLE (?:ONLY )?([\w.\"]+)\s+ADD CONSTRAINT (\S+) (.*)$", st, re.S)
        if m:
            tables.setdefault(m.group(1).replace("public.", "").strip('"'), {"columns": {}, "constraints": {}, "indexes": {}, "policies": {}, "rls": False})["constraints"][m.group(2).strip('"')] = re.sub(r"\s+", " ", m.group(3))
            continue
        m = re.match(r"CREATE (?:UNIQUE )?INDEX (\S+) ON (?:ONLY )?([\w.\"]+) (.*)$", st, re.S)
        if m:
            tables.setdefault(m.group(2).replace("public.", "").strip('"'), {"columns": {}, "constraints": {}, "indexes": {}, "policies": {}, "rls": False})["indexes"][m.group(1)] = re.sub(r"\s+", " ", st)
            continue
        m = re.match(r'CREATE POLICY (\S+) ON ([\w.\"]+)(.*)$', st, re.S)
        if m:
            tables.setdefault(m.group(2).replace("public.", "").strip('"'), {"columns": {}, "constraints": {}, "indexes": {}, "policies": {}, "rls": False})["policies"][m.group(1).strip('"')] = re.sub(r"\s+", " ", m.group(3)).strip()
            continue
        m = re.match(r"ALTER TABLE ([\w.\"]+) ENABLE ROW LEVEL SECURITY", st)
        if m:
            tables.setdefault(m.group(1).replace("public.", "").strip('"'), {"columns": {}, "constraints": {}, "indexes": {}, "policies": {}, "rls": False})["rls"] = True
    return tables


def diff_dicts(a, b):
    out = {}
    for k in sorted(set(a) | set(b)):
        if k not in a: out[k] = {"status": "new", "def": b[k]}
        elif k not in b: out[k] = {"status": "removed", "def": a[k]}
        elif a[k] != b[k]: out[k] = {"status": "changed", "def": b[k], "was": a[k]}
        else: out[k] = {"status": "same", "def": b[k]}
    return out


def cmd_schema(o):
    tag = re.sub(r"\W", "", o.prefix)
    bf, bd = build_db(o, o.base, f"{tag}_base")
    hf, hd = build_db(o, o.head, f"{tag}_head")
    out = Path(o.out); out.mkdir(parents=True, exist_ok=True)
    (out / "schema-base.sql").write_text(bd); (out / "schema-head.sql").write_text(hd)
    a, b = parse_dump(bd), parse_dump(hd)
    tables = {}
    for name in sorted(set(a) | set(b)):
        ta, tb = a.get(name), b.get(name)
        if ta is None: status = "new"
        elif tb is None: status = "removed"
        else: status = "changed" if json.dumps(ta, sort_keys=True) != json.dumps(tb, sort_keys=True) else "same"
        if status == "same" and not o.all:
            continue
        empty = {"columns": {}, "constraints": {}, "indexes": {}, "policies": {}, "rls": False}
        ta, tb = ta or empty, tb or empty
        tables[name] = {"status": status, "rls": tb["rls"], **{k: diff_dicts(ta[k], tb[k]) for k in ("columns", "constraints", "indexes", "policies")}}
    res = {"base": o.base, "head": o.head, "databases": {"base": f"{tag}_base", "head": f"{tag}_head"},
           "migrations": {"new": [f for f in hf if f not in bf], "removed": [f for f in bf if f not in hf],
                          "changed": [f for f in hf if f in bf and subprocess.run(["git", "-C", o.repo, "diff", "--quiet", o.base, o.head, "--", f]).returncode]},
           "tables": tables,
           "functions": {k: v for k, v in diff_dicts(parse_functions(bd), parse_functions(hd)).items() if v["status"] != "same"}}
    (out / "schema-diff.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: (v if k not in ("tables", "functions") else {t: d["status"] for t, d in v.items()}) for k, v in res.items()}, indent=1))


# ---- stats and dead code --------------------------------------------------------------------------------

def cmd_stats(o):
    files = adds = dels = tests = gen = 0
    for line in git(o.repo, "diff", "--numstat", f"{o.base}..{o.head}").splitlines():
        a, d, f = line.split("\t", 2)
        files += 1
        if a == "-": continue
        adds += int(a); dels += int(d)
        if re.search(r"(_test\.go|\.test\.[jt]sx?|\.spec\.[jt]sx?)$", f): tests += int(a)
        if re.search(o.generated, f): gen += int(a)
    commits = int(git(o.repo, "rev-list", "--count", f"{o.base}..{o.head}"))
    print(json.dumps({"files": files, "additions": adds, "deletions": dels, "commits": commits, "tests": tests, "generated": gen}))


def knip_findings(tree, config):
    if config:
        Path(tree, "knip.json").write_text(Path(config).read_text())
    r = subprocess.run(["bunx", "knip@5", "--reporter", "json"], cwd=tree, capture_output=True, text=True)
    if config:
        Path(tree, "knip.json").unlink()
    data = json.loads(r.stdout or "{}")
    out = {"files": sorted(data.get("files", []))}
    for issue in data.get("issues", []):
        for k in ("exports", "types", "dependencies", "devDependencies", "unlisted", "enumMembers", "duplicates"):
            v = issue.get(k) or []
            if isinstance(v, dict): v = [x for xs in v.values() for x in xs]
            for x in v:
                name = x["name"] if isinstance(x, dict) else str(x)
                out.setdefault(k, []).append({"file": issue["file"], "name": name, "line": x.get("line") if isinstance(x, dict) else None})
    return out


def go_findings(tree, go_dir, tags, goos):
    env = {**os.environ, **({"GOOS": goos} if goos else {})}
    gp = subprocess.run(["go", "env", "GOPATH"], capture_output=True, text=True).stdout.strip()
    tag = ["-tags", tags] if tags else []
    run = lambda *a: subprocess.run(list(a), cwd=Path(tree, go_dir), capture_output=True, text=True, env=env).stdout.splitlines()
    return {"deadcode": sorted(run(f"{gp}/bin/deadcode", *tag, "./...")), "deadcodeTest": sorted(run(f"{gp}/bin/deadcode", *tag, "-test", "./...")),
            "staticcheck": sorted(re.sub(r":\d+:\d+:", ":", l) for l in run(f"{gp}/bin/staticcheck", *tag, "-checks", "U1000", "./..."))}


def cmd_deadcode(o):
    res = {}
    if not o.skip_knip:
        kb, kh = knip_findings(o.base_dir, o.knip_config), knip_findings(o.head_dir, o.knip_config)
        key = lambda x: x if isinstance(x, str) else (x["file"], x["name"])
        res["knip"] = {}
        for k in sorted(set(kb) | set(kh)):
            b = {key(x): x for x in kb.get(k, [])}; h = {key(x): x for x in kh.get(k, [])}
            res["knip"][k] = {"base": len(b), "head": len(h), "new": [h[x] for x in h if x not in b], "gone": [b[x] for x in b if x not in h]}
    if o.go_dir and not o.skip_go:
        gb = go_findings(o.base_dir, o.go_dir, o.go_tags, o.goos); gh = go_findings(o.head_dir, o.go_dir, o.go_tags, o.goos)
        strip = lambda l: re.sub(r":\d+:\d+", "", l)
        res["go"] = {k: {"base": len(gb[k]), "head": len(gh[k]), "new": [l for l in gh[k] if strip(l) not in {strip(x) for x in gb[k]}],
                         "gone": [l for l in gb[k] if strip(l) not in {strip(x) for x in gh[k]}], "headAll": gh[k]} for k in gb}
    print(json.dumps(res, indent=1))


# ---- components -----------------------------------------------------------------------------------------

EXPORT_RE = re.compile(r"^export (?:default )?(?:function|const) ([A-Z]\w*)", re.M)
DECL_RE = re.compile(r"^(export )?(?:default )?(?:async )?(?:function|const|let|class) (\w+)", re.M)
TOP_RE = re.compile(r"^(?:export )?(?:default )?(?:async )?(?:function|const|let|type|interface|class|enum) ", re.M)


def bodies(text):
    """Each exported component's source: from its export to the next top-level declaration, plus the file's
    unexported helpers it uses, which often hold the JSX it draws."""
    starts = [m.start() for m in TOP_RE.finditer(text)] + [len(text)]
    decls = {}
    for m in DECL_RE.finditer(text):
        nxt = next(x for x in starts if x > m.start())
        decls[m.group(2)] = (bool(m.group(1)), text[m.start():nxt])
    out = {}
    for name, (exported, own) in decls.items():
        if not exported or not name[0].isupper() or name.isupper():
            continue
        parts, seen, todo = [own], {name}, [own]
        while todo:
            for w in set(re.findall(r"[A-Za-z_]\w*", todo.pop())):
                if w in decls and w not in seen and not decls[w][0]:
                    seen.add(w); parts.append(decls[w][1]); todo.append(decls[w][1])
        out[name] = "\n".join(parts)
    return out


def cmd_components(o):
    """The PR's new and changed components (each one whose own source changed, not every export of a changed
    file), which of the others each draws (JSX use, not imports), and how many levels of them sit beneath it,
    so the canvas can run bottom-up."""
    root = o.frontend.rstrip("/") + "/"
    files = [f for f in changed(o.repo, o.base, o.head) if f.startswith(root) and f.endswith(".tsx")
             and not re.search(r"\.(test|spec|catalog|stories)\.tsx$", f)
             # The catalog's own support code stages components; it isn't one of the product's.
             and not re.search(r"(^|/)catalog/", f[len(root):])]
    comps, unchanged = {}, []
    for f in files:
        head = bodies(git(o.repo, "show", f"{o.head}:{f}", check=False))
        base = bodies(git(o.repo, "show", f"{o.base}:{f}", check=False))
        for name, body in head.items():
            if base.get(name) == body:
                unchanged.append(name)
                continue
            comps[name] = {"file": f[len(root):], "status": "changed" if name in base else "new", "madeOf": [], "usedIn": [], "_body": body}
    names = set(comps) | set(unchanged)
    for name, c in comps.items():
        c["madeOf"] = sorted(n for n in comps if n != name and re.search(rf"<{n}[\s/>]", c["_body"]))
        c["drawsUnchanged"] = sorted(n for n in unchanged if n != name and re.search(rf"<{n}[\s/>]", c["_body"]))
    for name, c in comps.items():
        for n in c["madeOf"]:
            comps[n]["usedIn"].append(name)
    depth = {}
    def level(n, seen=()):
        if n in depth: return depth[n]
        if n in seen: return 0
        depth[n] = 1 + max((level(m, seen + (n,)) for m in comps[n]["madeOf"]), default=-1)
        return depth[n]
    for n in comps:
        comps[n]["level"] = level(n)
        del comps[n]["_body"]
    removed = [f[len(root):] for f in git(o.repo, "diff", "--name-only", "--diff-filter=D", f"{o.base}..{o.head}").splitlines()
               if f.startswith(root) and f.endswith(".tsx")]
    print(json.dumps({"components": dict(sorted(comps.items(), key=lambda kv: (kv[1]["level"], kv[1]["file"]))),
                      "unchangedInChangedFiles": sorted(unchanged), "removedFiles": removed}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", required=True)
    common.add_argument("--base"); common.add_argument("--head")
    common.add_argument("--migrations", default="**/migrations/*.sql", help="glob of migration files, relative to the repository")
    common.add_argument("--catalog", default="", help="the catalog's folder, from .5k/pr-review.yaml")
    common.add_argument("--generated", default=r"generated|\.gen\.|/bindings/", help="regex for generated files")
    p = sub.add_parser("changes", parents=[common]); p.add_argument("--since", help="the head the canvas was last built from")
    p = sub.add_parser("checkout", parents=[common]); p.add_argument("--dir", required=True); p.add_argument("--ref", required=True); p.add_argument("--no-install", action="store_true")
    p = sub.add_parser("schema", parents=[common]); p.add_argument("--format", choices=["goose", "plain"], default="plain")
    p.add_argument("--out", required=True); p.add_argument("--prefix", default="pr_review"); p.add_argument("--setup", help="SQL to run before the migrations, such as roles they grant to")
    p.add_argument("--all", action="store_true", help="include unchanged tables")
    sub.add_parser("stats", parents=[common])
    p = sub.add_parser("components", parents=[common]); p.add_argument("--frontend", default="frontend", help="the frontend's folder, which paths are given relative to")
    p = sub.add_parser("deadcode", parents=[common]); p.add_argument("--base-dir", required=True); p.add_argument("--head-dir", required=True)
    p.add_argument("--knip-config"); p.add_argument("--go-dir"); p.add_argument("--go-tags"); p.add_argument("--goos")
    p.add_argument("--skip-knip", action="store_true"); p.add_argument("--skip-go", action="store_true")
    o = ap.parse_args()
    {"changes": cmd_changes, "checkout": cmd_checkout, "schema": cmd_schema, "stats": cmd_stats, "deadcode": cmd_deadcode, "components": cmd_components}[o.cmd](o)


if __name__ == "__main__":
    main()
