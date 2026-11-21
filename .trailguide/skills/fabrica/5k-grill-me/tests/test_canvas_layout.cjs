const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/canvas.html'), 'utf8');
const example = JSON.parse(fs.readFileSync(path.join(__dirname, '../examples/design.json'), 'utf8'));
const layout = source.slice(source.indexOf('      function layout()'), source.indexOf('      function draw()'));
for (const compactTree of [false, true]) {
  const context = {session:example, compactTree, positions:{}};
  vm.createContext(context); vm.runInContext(layout + ';layout();', context);
  const positions = context.positions;
  for (const [id, a] of Object.entries(positions)) {
    for (const [other, b] of Object.entries(positions)) {
      if (id === other) continue;
      assert(a.x + 214 <= b.x || b.x + 214 <= a.x || a.y + 86 <= b.y || b.y + 86 <= a.y, `${id} overlaps ${other}`);
    }
  }
  for (const parent of example.nodes) {
    const children = example.nodes.filter(n => n.parentId === parent.id);
    for (const child of children) assert(positions[child.id].y > positions[parent.id].y + 86);
    if (!compactTree && children.length) {
      assert.equal(positions[parent.id].x, (positions[children[0].id].x + positions[children.at(-1).id].x) / 2);
    }
  }
  if (!compactTree) assert(positions.Q7.x - positions.Q6.x > positions.Q6.x - positions.Q5.x, 'Independent branches need more space than siblings');
}
const geometry = source.slice(source.indexOf('      function newArtifactView('), source.indexOf('      function openArtifact('));
for (const w of [320, 800, 1200]) for (const h of [360, 800]) for (const offset of [0,22,44]) for (const scale of [0.12, 0.75, 1, 2]) {
  const context = {available:()=>({w,h}),positions:{},pan:{x:-400,y:120,scale}};
  vm.createContext(context);vm.runInContext(geometry,context);
  const view = context.newArtifactView(offset);
  assert(context.artifactVisible(view), `New document must be reachable at width ${w}, zoom ${scale}`);
  assert(view.width * scale <= w - 32);
  assert(!context.artifactVisible({...view,x:100000}));
  assert(!context.artifactVisible({...view,y:-100000}));
}

const roomy = {available:()=>({w:1200,h:1000}),positions:{Q1:{x:0,y:316}},pan:{x:0,y:135,scale:1}};
vm.createContext(roomy);vm.runInContext(geometry,roomy);
const documentBelow = roomy.newArtifactView();
assert(documentBelow.y > roomy.positions.Q1.y + 86, 'Default document should avoid questions when there is room below');
assert(documentBelow.y + documentBelow.height + roomy.pan.y <= 920);

console.log('PASS nonoverlapping forest, parent alignment, branch spacing, and document placement at desktop/mobile zoom levels');
