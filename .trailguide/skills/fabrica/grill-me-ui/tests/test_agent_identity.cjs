const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/canvas.html'), 'utf8');
const context = { connection: { provider: 'codex' } };
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('      const agentMarks'), source.indexOf('      function updatePresence')), context);
const codex = context.agentIdentity();
assert.equal(codex.name, 'Codex');
assert(codex.icon.includes('class="agent-mark"'));
context.connection.provider = 'claude';
const claude = context.agentIdentity();
assert.equal(claude.name, 'Claude Code');
assert(claude.icon.includes('class="agent-mark"'));
assert.notEqual(codex.icon, claude.icon);
for (const provider of [undefined, 'unknown', 'toString', '<script>']) {
  context.connection.provider = provider;
  const fallback = context.agentIdentity();
  assert.equal(fallback.name, 'Agent');
  assert(fallback.icon.includes('class="agent-icon"'));
}
console.log('PASS linked provider identity, distinct embedded brand icons and safe generic fallback');

// Connection states remain honest as the server, listener and transport change.
const elements = new Map();
context.$ = id => {
  if (!elements.has(id)) elements.set(id, {hidden:false,attrs:{},classList:{toggle(){}},setAttribute(name,value){this.attrs[name]=value;}});
  return elements.get(id);
};
context.renderInterviewStatus = () => {};
context.bridge = {}; context.connected = true; context.listening = false;
context.connection = {provider:'codex',sessionId:'test-session',transport:'inbox'};
vm.runInContext(source.slice(source.indexOf('      function directDelivery('), source.indexOf('      function replyStatus(')), context);
vm.runInContext(source.slice(source.indexOf('      function updatePresence('), source.indexOf('      // Keep the layout stable')), context);
context.inbox = [];
vm.runInContext(fs.readFileSync(path.join(__dirname, '../assets/question-help.js'), 'utf8'), context);
const label = () => {context.updatePresence();return context.$('presenceLabel').textContent;};
assert.equal(label(),'Copy & paste');
assert(context.$('connectionInfo').textContent.includes('manually copying'));
assert.equal(context.$('copyChatId').hidden,false);
assert.equal(context.$('presence').attrs['aria-label'],'Codex: Copy & paste. Connection details');
context.listening = true; assert.equal(label(),'Connected');
context.listening = false; context.connection.transport = 'codex-queue'; assert.equal(label(),'Connected');
assert(context.$('connectionInfo').textContent.includes('automatically'));
context.connected = false; assert.equal(label(),'Connection lost');
assert(context.$('connectionInfo').textContent.includes('unavailable'));
context.bridge = null; assert.equal(label(),'Copy & paste');
context.renderInterviewStatus = () => {};
context.bridge = {}; context.connected = true; context.listening = false; context.connection = {};
assert.equal(label(),'Copy & paste'); assert.equal(context.$('copyChatId').hidden,true);
assert(context.$('connectionInfo').textContent.includes('your agent chat'));
console.log('PASS agent connection status and guidance for listener, direct delivery, offline, standalone and unbound sessions');

context.connection={provider:'codex',transport:'inbox'}; context.listening=true;
context.inbox=[{kind:'help',nodeId:'Q1'}];
assert.equal(label(),'Waiting for agent');
context.inbox[0].receivedAt=123;
assert.equal(label(),'Explaining');
assert(context.$('connectionInfo').textContent.includes('answers are unchanged'));
context.inbox[0].delivery={status:'failed'};
assert.equal(label(),'Connected','Failed help delivery must not imply active processing');
context.inbox=[];
console.log('PASS help receipt activity is distinct from answer review');
