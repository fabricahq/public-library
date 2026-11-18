const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/canvas.html'), 'utf8');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../examples/design-context.json')));
const c = {session:fixture,pending:()=>null, esc:s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))};
vm.createContext(c);
vm.runInContext(source.slice(source.indexOf('      function decisionContext'), source.indexOf('      function responseContent')), c);
vm.runInContext(source.slice(source.indexOf('      function designArtifacts'), source.indexOf('      function renderArtifactList')), c);
let node = fixture.nodes[0], html = c.decisionContext(node);
for (const label of ['Assumptions','Explore alternatives','Related examples','Applicable constraints']) assert(html.includes(label));
assert(!html.includes('<details open'), 'Context is collapsed by default');
assert(html.includes(node.assumptions[0].statement));
assert(html.includes(node.alternatives[0].description));
assert(html.includes(node.precedents[0].insight));
assert(!html.includes('type="submit"'), 'Exploring cannot submit or replace an answer');
assert.equal(c.decisionContext({answer:null}), '');
assert(c.decisionContext(fixture.nodes[1]).includes('Additional context'));
assert(c.decisionContext(fixture.nodes[1]).includes(fixture.nodes[1].notes));
assert(c.decisionContext({...node,notes:'<script>bad</script>'}).includes('&lt;script&gt;'));
assert(!c.decisionContext({...node,precedents:[{url:'javascript:alert(1)',title:'Unsafe',insight:'A useful comparison'}]}).includes('href="javascript:'));
const unlinked=c.decisionContext({precedents:[{title:'Project example',insight:'An <important> lesson'}]});
assert(unlinked.includes('Project example') && unlinked.includes('An &lt;important&gt; lesson'));
assert(!unlinked.includes('<a '), 'A precedent without a URL remains readable without a broken link');
assert.equal(c.decisionContext({assumptions:[],alternatives:[],precedents:[]}), '');
const docs=c.designArtifacts(fixture,[{id:'official',path:'/project/CONTEXT.md'}]);
assert.equal(docs.length,2);assert.equal(docs[0].id,'design-constraints');assert.equal(docs[0].path,null);
assert.equal(c.designArtifacts(fixture,docs).length,2, 'Refresh never duplicates the constraints document');
assert.equal(c.designArtifacts({...fixture,constraints:[]},docs).length,1,'Removing constraints removes their derived view');
const rendered=c.constraintsDocument([{id:'C1',statement:'<unsafe>',reason:'A & B'}]);
assert(rendered.includes('&lt;unsafe&gt;'));assert(rendered.includes('A &amp; B'));assert(rendered.includes('1 requirement the design must satisfy.'));
console.log('PASS contextual disclosures, safe evidence, derived constraints and removal');

const outline=[];
const constraintsHtml=c.constraintsDocument(fixture.constraints,outline);
assert.equal(outline.length,fixture.constraints.length);
outline.forEach((entry,index)=>{
 assert.equal(entry.title,fixture.constraints[index].id+' · '+fixture.constraints[index].statement);
 assert(constraintsHtml.includes('data-document-line="'+entry.line+'" tabindex="-1"'), 'Every contents item has a focusable jump target');
});
assert.equal(new Set(outline.map(e=>e.line)).size,outline.length);
console.log('PASS constraints contents entries match unique focusable requirements');

const scoped=c.decisionContext(fixture.nodes[1]);
for(const requirement of fixture.constraints) {
 assert.equal(scoped.includes(requirement.statement),fixture.nodes[1].constraintIds.includes(requirement.id),'Only constraints linked to this question are shown');
}
assert(scoped.includes('View all constraints'));
assert(!c.decisionContext({constraintIds:[]}).includes('Applicable constraints'));
console.log('PASS applicable constraints list includes only linked requirements');
