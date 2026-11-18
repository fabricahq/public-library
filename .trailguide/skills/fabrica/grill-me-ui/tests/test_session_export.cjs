const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/canvas.html'), 'utf8');
let preview, blob, filename, downloads=0;
const timers=new Map();let timerId=0;
const icon={innerHTML:"download-icon"};const attributes={};const classes=new Set();
const elements = {viewContext:{}, announcement:{}, downloadSession:{disabled:false,querySelector:()=>icon,
 setAttribute:(k,v)=>attributes[k]=v,removeAttribute:k=>delete attributes[k],
 classList:{add:c=>classes.add(c),remove:c=>classes.delete(c)}}, copyFeedback:{}};
const context = {
  downloadFeedbackReset:null, completedRevision:null,
  session:{id:'design',revision:3,constraints:[{id:'C1',statement:'Keep answers recoverable'}],nodes:[{id:'Q1',question:'Which format?',answer:'Markdown'}]},
  answerState:{Q1:{changedAt:2,confirmedAt:3}},
  drafts:{Q2:'Unfinished'},draftContexts:{Q2:{baseRevision:2}},inbox:[{nodeId:'Q1',text:'With examples'}],
  $:id => elements[id], openCopy:(text, options) => {preview = {text, options};},
  Blob, URL:{createObjectURL:value => {blob = value;return 'blob:test';},revokeObjectURL(){}},
  document:{createElement:() => ({click(){filename = this.download;downloads++;}})}, setTimeout:(fn,ms)=>{timers.set(++timerId,{fn,ms});return timerId;},clearTimeout:id=>timers.delete(id),
};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('      function sessionExport('),source.indexOf('      async function copyReply(')),context);
vm.runInContext(source.slice(source.indexOf('      $("viewContext").onclick'),source.indexOf('      $("closeDialog").onclick')),context);
vm.runInContext(source.slice(source.indexOf('      $("downloadSession").onclick'),source.indexOf('      $("copyChatId").onclick')),context);
(async () => {
  elements.viewContext.onclick();
  context.copySessionJson = preview.options.exportJson;
  assert(preview.text.endsWith(context.copySessionJson), 'copied message and JSON must share the same complete data');
  context.session.nodes[0].answer = 'Changed after preview opened';
  context.drafts.Q2 = 'Changed draft';
  elements.downloadSession.onclick();
  assert.equal(elements.downloadSession.disabled,true,'Disable duplicate downloads during feedback');
  assert.equal(attributes['aria-busy'],'true');assert(classes.has('is-downloading'));
  assert(icon.innerHTML.includes('<circle'),'Download icon becomes a progress indicator');
  assert.equal(elements.copyFeedback.textContent,'','No separate success-status row');
  elements.downloadSession.onclick();assert.equal(downloads,1,'Repeated click must not download twice');
  assert.equal(filename, 'grill-session.json');
  assert.equal(blob.type, 'application/json');
  const downloaded = await blob.text();
  assert.equal(downloaded, preview.options.exportJson, 'download must match the displayed snapshot even after live updates');
  const data = JSON.parse(downloaded);
  assert.equal(data.session.nodes[0].answer, 'Markdown');
  assert.equal(data.session.constraints[0].statement, 'Keep answers recoverable');
  assert.equal(data.drafts.Q2, 'Unfinished');
  assert.deepEqual(data.answerState.Q1,{changedAt:2,confirmedAt:3});
  assert.equal(data.pending[0].text, 'With examples');
  [...timers.values()].find(t=>t.ms===1500).fn();
  assert.equal(elements.downloadSession.disabled,false);assert.equal(icon.innerHTML,'download-icon');
  assert.equal(attributes['aria-busy'],undefined);assert(!classes.has('is-downloading'));
  context.copySessionJson = null;blob = null;
  elements.downloadSession.onclick();assert.equal(blob, null, 'single-answer or path dialogs must not export session data');
  context.copySessionJson = preview.options.exportJson;
  context.document.createElement=()=>{throw Error('download unavailable');};
  elements.downloadSession.onclick();
  assert.equal(elements.downloadSession.disabled,false,'Failed download must allow retry');
  assert.equal(attributes['aria-busy'],undefined);assert.equal(icon.innerHTML,'download-icon');
  assert(elements.copyFeedback.textContent.includes('Could not start'));
  console.log('PASS copy/download data parity, frozen preview, progress state, duplicate prevention, reset, failure recovery and unavailable export guard');
})().catch(error => {console.error(error);process.exitCode = 1;});
