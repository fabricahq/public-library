const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../assets/canvas.html'),'utf8');
const node=(id,parentId=null,answer='Yes',dependsOn=[])=>({id,title:id,question:`Question ${id}?`,parentId,answer,dependsOn});
const nodes=[node('Q1'),node('Q2','Q1'),node('Q3',null,'Yes',['Q2']),node('Q4'),node('Q5','Q3','Tentative')];
const c={session:{id:'test',revision:1,nodes},answerState:Object.fromEntries(nodes.map(n=>[n.id,{changedAt:1,confirmedAt:1}])),inbox:[{id:'b',kind:'answer',nodeId:'Q5',text:'Tentative'}],crypto:{randomUUID:()=> 'clear-id'},deps:n=>[n.parentId,...n.dependsOn].filter(Boolean),get:id=>nodes.find(n=>n.id===id)};
vm.createContext(c);
vm.runInContext(source.slice(source.indexOf('      function answerIsCurrent('),source.indexOf('      const labels =')),c);
vm.runInContext(source.slice(source.indexOf('      function recordLocalAnswer('),source.indexOf('      async function clearAnswer(')),c);
assert.equal(c.status(nodes[0]),'answered');
c.recordLocalAnswer(nodes[0],'New root answer');
assert.equal(nodes[0].answer,'New root answer');
assert.equal(c.status(nodes[1]),'review');assert.equal(c.status(nodes[2]),'review');assert.equal(c.status(nodes[3]),'answered');
c.recordLocalAnswer(nodes[1],nodes[1].answer);
assert.equal(c.status(nodes[1]),'answered');assert.equal(c.status(nodes[2]),'review');
assert.equal(c.answerState.Q2.changedAt,1,'Keeping an answer confirms it without changing it');
c.recordLocalAnswer(nodes[2],nodes[2].answer);
assert.equal(c.status(nodes[2]),'answered');
const event=c.clearLocalAnswer(nodes[0]);
assert.equal(nodes[0].answer,null);assert.equal(c.status(nodes[0]),'open');
assert.equal(nodes[1].answer,'Yes');assert.equal(c.status(nodes[1]),'review');assert.equal(c.status(nodes[2]),'review');
assert.equal(c.status(nodes[3]),'answered');assert.equal(c.status(nodes[4]),'review');
assert.equal(event.previousAnswer,'New root answer');assert.equal(c.inbox.find(e=>e.kind==='clear').nodeId,'Q1');
c.recordLocalAnswer(nodes[0],'New root answer');
assert.equal(c.status(nodes[1]),'review','Re-answering the parent does not confirm its dependents');
assert(nodes.every(n=>!('needsReview' in n)));
console.log('PASS immediate standalone answers, confirmations, transitive review, clears and unrelated preservation');

// Shared prerequisite paths must be evaluated once, not once per path.
for(let i=6;i<=70;i++){
 const n=node('Q'+i,null,'Yes',i===6?['Q4']:['Q'+(i-1),i>7?'Q'+(i-2):'Q4']);
 nodes.push(n);c.answerState[n.id]={changedAt:1,confirmedAt:1};
}
assert.equal(c.status(nodes.at(-1)),'answered');
c.recordLocalAnswer(nodes[3],'Changed independent root');
assert.equal(c.status(nodes.at(-1)),'review');
