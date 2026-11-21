// Reads each component's properties from its source: the type of its first parameter, with each
// property's declared type, whether it is optional, and its doc comment. Uses the project's own TypeScript.
// Usage: node props.cjs <frontend dir> '<json list of [file, exportName, key?]>'  -> JSON {key: [{name,type,optional,doc}] | null}
const path = require('path');
const root = process.argv[2];
const ts = require(require.resolve('typescript', { paths: [root, path.join(root, '..')] }));
const list = JSON.parse(process.argv[3]);
const files = list.map(([f]) => path.join(root, f)).filter((f) => require('fs').existsSync(f));
const cfgPath = path.join(root, 'tsconfig.json');
const cfg = ts.parseJsonConfigFileContent(ts.readConfigFile(cfgPath, ts.sys.readFile).config, ts.sys, root);
const program = ts.createProgram(files, cfg.options);
const checker = program.getTypeChecker();
const out = {};
for (const [f, name, key] of list) {
  const sf = program.getSourceFile(path.join(root, f));
  if (!sf) { out[key || name] = null; continue; }
  const sym = checker.getExportsOfModule(checker.getSymbolAtLocation(sf)).find((s) => s.name === name);
  if (!sym) { out[key || name] = null; continue; }
  const decl = (sym.flags & ts.SymbolFlags.Alias ? checker.getAliasedSymbol(sym) : sym).declarations[0];
  let fn = decl;
  if (ts.isVariableDeclaration(decl)) fn = decl.initializer;
  const param = fn && fn.parameters && fn.parameters[0];
  if (!param) { out[key || name] = []; continue; }
  const t = checker.getTypeAtLocation(param);
  out[key || name] = t.getProperties().map((p) => {
    const d = p.valueDeclaration || p.declarations?.[0];
    const typeText = d && d.type ? d.type.getText().replace(/\s+/g, ' ') : checker.typeToString(checker.getTypeOfSymbolAtLocation(p, param));
    return { name: p.name, type: typeText, optional: !!(p.flags & ts.SymbolFlags.Optional), doc: ts.displayPartsToString(p.getDocumentationComment(checker)).replace(/\s+/g, ' ') };
  });
}
console.log(JSON.stringify(out, null, 1));
