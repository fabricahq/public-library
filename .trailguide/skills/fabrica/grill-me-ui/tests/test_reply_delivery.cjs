const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/canvas.html'), 'utf8');
let copied = [], fallback = [], notices = [];
const context = {completedRevision:null,connected:true, listening:false, navigator:{clipboard:{writeText:async text=>copied.push(text)}},
 showCopySuccess:button=>notices.push(button), openCopy:text=>fallback.push(text), setTimeout, clearTimeout};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('      function replyStatus('), source.indexOf('      // Brand paths')),context);
vm.runInContext(source.slice(source.indexOf('      async function copyReply('), source.indexOf('      let copyReturnTarget')),context);
assert.match(context.pendingHint({}), /paste it into your agent chat/);
assert.match(context.replyStatus({delivery:{status:'queued'}}),/Sending/);
assert.match(context.replyStatus({receivedAt:1}),/Received/);
context.listening=true;assert.match(context.pendingHint({receivedAt:1}),/Preparing your next question/);
assert.match(context.pendingHint({}), /Waiting for the agent/);
assert.match(context.pendingHint({delivery:{status:'sent'}}), /Accepted by Codex/);
assert.match(context.pendingHint({delivery:{status:'unknown'}}), /Check your agent chat before sending again/);
assert.match(context.pendingHint({delivery:{status:'failed'}}), /Could not send/);
// Both scopes must carry enough context for a fresh agent chat.
Object.assign(context, {session:{id:'design',title:'Design title',revision:4,nodes:[{id:'Q1',question:'Which format?',answer:'Markdown'}]},
 bridge:{sessionDir:'/project/design'},connection:{provider:'codex',sessionId:'chat-123'},answerState:{},drafts:{Q2:'Unfinished'},draftContexts:{Q2:{baseRevision:3}},inbox:[{nodeId:'Q1',text:'Markdown, with examples.'}]});
vm.runInContext(source.slice(source.indexOf('      function replyMessage('),source.indexOf('      const copyFeedbackTimers')),context);
const question={id:'Q1',title:'File format',question:'Which format?',answer:null};
const answer='Markdown.\n\nInclude code examples and preserve all details.';
const single=context.replyMessage(question,answer,{baseRevision:3,question:'Which format?',previousAnswer:null});
assert(single.includes('Q1: File format'));assert(single.includes('Which format?'));assert(single.includes(answer));
assert(single.includes('Session: design'));assert(single.includes('snapshot revision: 3'));
const all=JSON.parse(context.sessionMessage().split('\n\n').slice(1).join('\n\n'));
assert.equal(all.session.nodes[0].question,'Which format?');assert.equal(all.session.nodes[0].answer,'Markdown');
assert.equal(all.pending[0].text,'Markdown, with examples.');assert.equal(all.drafts.Q2,'Unfinished');
(async()=>{
 const message='Q8: Yes.\nOriginal revision: 3';
 const guidance={textContent:''}; const button={isConnected:true,textContent:'Copy answer',closest:()=>({querySelector:()=>guidance})};
 await context.copyReply(message,button);assert.equal(button.textContent,'Copy answer');assert.equal(guidance.textContent,'');assert.deepEqual(copied,[message]);assert.equal(fallback.length,0);assert.equal(notices[0],button);
 context.navigator.clipboard.writeText=async()=>{throw Error('denied')};
 await context.copyReply(message);assert.deepEqual(fallback,[message]);assert.equal(notices.length,1);
 context.navigator.clipboard.writeText=()=>new Promise(()=>{});
 await context.copyReply(message);assert.equal(fallback.length,2);assert.equal(notices.length,1);
 console.log('PASS saved, listening, sent and uncertain delivery guidance; one-click copy and manual fallback');
})().catch(error=>{console.error(error);process.exitCode=1});
