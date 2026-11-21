const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/canvas.html'), 'utf8');
const start = source.indexOf('      function markdownSource(');
const end = source.indexOf('      const fileIcon', start);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const {markdownSource, documentSource, resizedArtifact} = new Function('esc',source.slice(start,end)+';return {markdownSource,documentSource,resizedArtifact};')(esc);
const samples = [
  '# Heading\n\n**Bold** and *italic* with `code` and [link](https://example.com).\n',
  '> Quote\n- Item\n1. First\n---\n',
  '```html\n<script>alert("x")</script>\n**not emphasis**\n```\n',
  '~~~~md\n# Code\n~~~\nstill code\n~~~~\n',
  '<img src=x onerror=alert(1)> & &#39; <span class="md-heading">fake</span>\n',
  'Unicode: café 🪴\r\n\tTabbed\r\n\n'
];
const decode = s => s.replace(/&(amp|lt|gt|quot|#39);/g,(_,x)=>({amp:'&',lt:'<',gt:'>',quot:'"','#39':"'"}[x]));
for (const text of samples) {
  const html = markdownSource(text);
  assert.equal(decode(html.replace(/<\/?span(?: class="md-[a-z]+")?>/g,'')),text,'Source must preserve every original character');
  assert(!/<(?:script|img)\b/i.test(html),'HTML in files must stay inert');
  const navigable = documentSource(text,[{line:0},{line:2}]);
  assert.equal(decode(navigable.replace(/<\/?span[^>]*>/g,'')),text,'Navigation anchors must preserve exact source');
}
assert(markdownSource('# Heading').includes('class="md-heading"'));
assert(markdownSource('**Bold**').includes('class="md-emphasis"'));
assert(markdownSource('[a](b)').includes('class="md-link"'));
assert(!markdownSource('```\n**literal**\n```').includes('md-emphasis'));
const initial = {x:50,y:70,width:400,height:300,source:true};
for (const edge of ['n','e','s','w','ne','nw','sw','se']) {
  const grown = resizedArtifact(initial, edge, edge.includes('w')?-120:120,edge.includes('n')?-80:80,280,200);
  assert.equal(grown.width,edge.includes('w')||edge.includes('e')?520:400);
  assert.equal(grown.height,edge.includes('n')||edge.includes('s')?380:300);
  if (edge.includes('w')) assert.equal(grown.x+grown.width,initial.x+initial.width);
  if (edge.includes('n')) assert.equal(grown.y+grown.height,initial.y+initial.height);
  const clamped = resizedArtifact(initial, edge,edge.includes('w')?10000:-10000,edge.includes('n')?10000:-10000,280,200);
  assert(clamped.width>=280 && clamped.height>=200);
  assert.equal(clamped.source,true);
}
assert.deepEqual(initial,{x:50,y:70,width:400,height:300,source:true},'Resizing must not mutate the starting bounds');
console.log('PASS exact and inert highlighted Markdown, fences, all resize edges, anchored corners and minimum sizes');

const boundsCode = source.slice(source.indexOf('      function visibleArtifactBounds('), source.indexOf('      function positionArtifactWindows('));
let docked = true;
const bounds = new Function('document','innerWidth','available','pan',boundsCode+';return visibleArtifactBounds;')(
  {body:{matches:()=>docked}},390,()=>({w:390,h:229}),{x:40,y:60,scale:0.75});
const saved = {x:120,y:100,width:640,height:700};
const visible = bounds(saved);
assert(visible.x*0.75+40>=16 && visible.y*0.75+60>=16);
assert((visible.x+visible.width)*0.75+40<=374);
assert((visible.y+visible.height)*0.75+60<=213);
assert.equal(saved.height,700,'Docking must preserve the saved window size');
docked=false;
assert.strictEqual(bounds(saved),saved,'Closing the dock restores the original bounds');
console.log('PASS temporary mobile dock bounds keep controls reachable without losing saved dimensions');
