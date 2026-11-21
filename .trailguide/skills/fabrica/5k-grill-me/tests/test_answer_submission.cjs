const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../assets/canvas.html'),'utf8');
const n={id:'Q1',title:'Storage',question:'Where?',answer:'Local'};
const c={session:{id:'test',revision:1,nodes:[n]},answerState:{Q1:{changedAt:1,confirmedAt:1}},
 drafts:{Q1:'Cloud'},draftContexts:{Q1:{baseRevision:1,previousAnswer:'Local'}},inbox:[],
 submissionCache:{},answerModes:{},sending:false,followupRequest:null,bridge:{base:'/'},
 get:id=>c.session.nodes.find(node=>node.id===id),deps:node=>[...(node.parentId?[node.parentId]:[]),...(node.dependsOn||[])],
 pending:()=>null,draftContext:()=>c.draftContexts.Q1,currentContext:()=>({baseRevision:c.session.revision,previousAnswer:n.answer}),
 crypto:{randomUUID:()=> 'test-receipt'},commitStandalone:async change=>change(),renderPanel:()=>{},saveDrafts:()=>{},draw:()=>{},refresh:async()=>{},toast:()=>{}, $:()=>({hidden:false})};
vm.createContext(c);
vm.runInContext(source.slice(source.indexOf('      function recordLocalAnswer('),source.indexOf('      function clearLocalAnswer(')),c);
vm.runInContext(source.slice(source.indexOf('      async function send('),source.indexOf('      // Escape source')),c);
(async()=>{
 c.fetch=async()=>({ok:false,json:async()=>({error:'Conflict'})});
 await c.send(n);assert.equal(c.drafts.Q1,'Cloud');assert(c.submissionCache.Q1);assert.equal(n.answer,'Local');
 c.fetch=async()=>({ok:true,json:async()=>({status:'saved'})});
 await c.send(n);assert.equal(c.drafts.Q1,undefined);assert.equal(c.draftContexts.Q1,undefined);assert.equal(c.submissionCache.Q1,undefined);
 c.drafts.Q1='Cloud';c.draftContexts.Q1={baseRevision:1,previousAnswer:'Local'};
 c.fetch=async()=>{c.drafts.Q1='Cloud, with encryption';return {ok:true,json:async()=>({status:'saved'})};};
 await c.send(n);assert.equal(c.drafts.Q1,'Cloud, with encryption','An edit made during submission remains a draft');
 c.bridge=null;c.drafts.Q1='Cloud';await c.send(n);
 assert.equal(n.answer,'Cloud');assert.equal(c.session.revision,2);assert.equal(c.drafts.Q1,undefined);
 assert.equal(c.inbox[0].text,'Cloud');assert.equal(c.inbox[0].previousAnswer,'Local');
 console.log('PASS failed submission preserves drafts, success consumes matching draft, concurrent edits survive, standalone submission updates answer');
})().catch(error=>{console.error(error);process.exitCode=1});
