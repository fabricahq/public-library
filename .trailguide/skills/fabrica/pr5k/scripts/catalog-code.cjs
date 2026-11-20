// Usage: node catalog-code.cjs <frontend dir> <catalog file relative to it>...
// Expects catalog files that declare entries as object literals with `component` and `states`, each state
// with `id`, `title`, `render` and optional `controls` (each with an `initial`). Other layouts: write the code by hand.
// Prints, per component and state, the code that state runs, read from its catalog file:
// the imports it uses, its controls' starting values, the element its render returns,
// and the file's own helper components it calls.
const fs = require('fs'), path = require('path');
const [root, ...files] = process.argv.slice(2);
const ts = require(require.resolve('typescript', { paths: [root, path.join(root, '..')] }));
const dedent = (t) => { const lines = t.split('\n'); const ind = Math.min(...lines.slice(1).filter((l) => l.trim()).map((l) => l.match(/^ */)[0].length), Infinity); return [lines[0], ...lines.slice(1).map((l) => l.slice(ind === Infinity ? 0 : ind))].join('\n'); };
const out = {};
for (const rel of files) {
  const text = fs.readFileSync(path.join(root, rel), 'utf8');
  const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const src = (n) => text.slice(n.getStart(sf), n.end);
  const imports = sf.statements.filter(ts.isImportDeclaration);
  const helpers = new Map();
  for (const st of sf.statements) {
    if (ts.isFunctionDeclaration(st) && st.name) helpers.set(st.name.text, st);
    if (ts.isVariableStatement(st)) for (const d of st.declarationList.declarations) if (ts.isIdentifier(d.name) && d.name.text !== 'catalogEntries') helpers.set(d.name.text, st);
    if (ts.isTypeAliasDeclaration(st)) helpers.set(st.name.text, st);
  }
  const prop = (o, k) => o.properties.find((p) => p.name && p.name.getText(sf) === k);
  const used = (code) => new Set(code.match(/[A-Za-z_$][\w$]*/g));
  const visit = (n) => {
    if (ts.isObjectLiteralExpression(n) && prop(n, 'component') && prop(n, 'states')) {
      const component = JSON.parse(prop(n, 'component').initializer.getText(sf).replace(/'/g, '"'));
      const states = {};
      for (let el of prop(n, 'states').initializer.elements) {
        if (ts.isCallExpression(el)) el = el.arguments[0];
        if (!ts.isObjectLiteralExpression(el)) continue;
        const id = prop(el, 'id').initializer.text, title = prop(el, 'title').initializer.text;
        const r = prop(el, 'render'); const fn = ts.isMethodDeclaration(r) ? r : r.initializer;
        let body = fn.body; if (ts.isParenthesizedExpression(body)) body = body.expression;
        const lines = [];
        const controls = prop(el, 'controls');
        if (controls && fn.parameters[0] && ts.isObjectBindingPattern(fn.parameters[0].name)) {
          const init = controls.initializer.properties.map((p) => [p.name.getText(sf), src(prop(p.initializer, 'initial').initializer)]);
          lines.push(...init.map(([k, v]) => `const ${k} = ${v}; // a control on the catalog page`), '');
        }
        let code = dedent(src(body));
        // The file's own helpers the element uses, then any they use in turn.
        const seen = new Set(), add = [];
        const walk = (c) => { for (const w of used(c)) if (helpers.has(w) && !seen.has(w)) { seen.add(w); const h = src(helpers.get(w)); add.push(h); walk(h); } };
        walk(code);
        const all = [...lines, code, ...add.map((h) => '\n' + h)].join('\n');
        const names = used(all);
        const imps = imports.map((d) => {
          const c = d.importClause; if (!c) return null;
          const keep = [];
          if (c.name && names.has(c.name.text)) keep.push(c.name.text);
          if (c.namedBindings && ts.isNamedImports(c.namedBindings)) {
            const el = c.namedBindings.elements.filter((e) => names.has(e.name.text)).map((e) => e.getText(sf));
            if (el.length) keep.push(`{ ${el.join(', ')} }`);
          }
          return keep.length ? `import ${c.isTypeOnly ? "type " : ""}${keep.join(', ')} from ${d.moduleSpecifier.getText(sf)};` : null;
        }).filter(Boolean);
        states[id] = { title, code: [...imps, ...(imps.length ? [''] : []), all].join('\n').replace(/\n{3,}/g, '\n\n') };
      }
      out[component] = { catalogFile: rel, states };
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
}
console.log(JSON.stringify(out, null, 1));
