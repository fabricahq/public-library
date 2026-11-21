const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../assets/canvas.html'),'utf8');
const functions=source.slice(source.indexOf('      function newQuestionMark('),source.indexOf('      function nextReadyQuestion('));
function run({busy=false,selected='Q1',ack=true,ready=true,newNode=true,request=true,settledAnswer=true}={}){
 const old={nodes:[{id:'Q1',ready:true},{id:'Q2',ready:true},{id:'Q3',ready:false}]};
 const session={nodes:[{id:'Q1',answer:settledAnswer?'Yes':null,ready:false},{id:'Q2',ready:true},{id:'Q3',ready:true},...(newNode?[{id:'Q4',ready}]:[])]};
 const c={session,selected,acknowledged:ack?['reply']:[],followupRequest:request?{nodeId:'Q1',eventId:'reply'}:null,newQuestionIds:new Set(),get:id=>session.nodes.find(n=>n.id===id),isFrontier:n=>n.ready,settled:n=>!!n?.answer};
 c.confidenceMode="tree";c.confidenceMatches=()=>true;vm.createContext(c);vm.runInContext(functions,c);
 const next=c.applyInterviewUpdate(old,new Set(['Q1','Q2']),busy);
 return {c,next,old};
}
assert.equal(run().next,'Q4','advance to newly added ready follow-up despite another open branch');
assert.equal(run({ready:false}).next,'Q3','skip blocked new question and prefer newly unlocked one');
assert.equal(run({newNode:false}).next,'Q3');
for(const options of [{busy:true},{selected:'Q2'},{selected:null},{ack:false},{request:false},{settledAnswer:false}]){
 const {c,next}=run(options);assert.equal(next,null,'never advance during unrelated activity or without acknowledgment');assert(c.newQuestionIds.has('Q4'),'new questions remain discoverable');
}
const {c,old}=run();
c.newQuestionIds.add('Q2');c.followupRequest={nodeId:'Q1',eventId:'reply'};assert.equal(c.applyInterviewUpdate(old,new Set(['Q1','Q2']),false),'Q4','latest follow-up precedes an older unread question');assert.equal(c.followupRequest,null,'consume advancement once');
assert.equal(c.applyInterviewUpdate(c.session,new Set(['Q2','Q3','Q4']),false),null,'repeated poll does not navigate again');
assert.equal(c.newQuestionMark({id:'Q4'}),'<span class="new-question">New</span>');
assert.equal(run().c.newQuestionMark({id:'Q2'}),'','existing open question is not new');
c.session.nodes=c.session.nodes.filter(n=>n.id!=='Q4');c.applyInterviewUpdate(old,new Set(),false);assert(!c.newQuestionIds.has('Q4'),'remove stale markers');
const scale=0.8;c.pan={x:0,y:0,scale};c.positions={Q2:{x:1500,y:900}};c.available=()=>({w:700,h:500});c.transform=()=>{};
c.revealQuestion('Q2');assert.equal(c.pan.scale,scale,'advancement preserves zoom');
assert(c.positions.Q2.x*scale+c.pan.x>=20 && c.positions.Q2.x*scale+c.pan.x+214*scale<=680,'target is visible horizontally');
assert(c.positions.Q2.y*scale+c.pan.y>=20 && c.positions.Q2.y*scale+c.pan.y+86*scale<=480,'target is visible vertically');
console.log('PASS one-answer advancement, new-question priority, no focus stealing, no repeated navigation and visible target without zoom changes');
