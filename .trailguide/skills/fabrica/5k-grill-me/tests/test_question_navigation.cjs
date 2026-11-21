const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/canvas.html'), 'utf8');
const functions = source.slice(source.indexOf('      function nextReadyQuestion('), source.indexOf('      function renderPanel('));
const nodes = [{id:'Q1'}, {id:'Q2'}, {id:'Q3'}, {id:'Q4'}];
const context = {newQuestionIds:new Set(),session:{nodes},selected:null,isFrontier:n=>n.ready,pending:()=>null,status:n=>n.answer ? "answered" : "waiting",connected:true,listening:false,copyIcon:()=>"<svg></svg>",esc:String};
context.confidenceMatches=()=>true;vm.createContext(context); vm.runInContext(functions,context);
nodes[1].ready = nodes[3].ready = true;
assert.equal(context.nextReadyQuestion().id,'Q2');
context.selected = 'Q2'; assert.equal(context.nextReadyQuestion().id,'Q4');
context.selected = 'Q4'; assert.equal(context.nextReadyQuestion().id,'Q2','wrap to first eligible question');
context.selected = 'Q3'; assert.equal(context.nextReadyQuestion().id,'Q4','continue after the selected saved question');
nodes[3].ready = false;
assert.equal(context.nextReadyQuestion().id,'Q2','skip ineligible questions');
context.selected = 'Q2'; assert.equal(context.nextReadyQuestion(),undefined,'do not navigate to the current question');
assert(context.questionNavigation().includes('View remaining question'), 'Blocked questions remain discoverable');
nodes[1].ready = false; assert.equal(context.nextReadyQuestion(),undefined);
context.selected = 'removed'; nodes[3].ready = true; assert.equal(context.nextReadyQuestion().id,'Q4');
nodes[1].ready=true;context.selected='Q1';context.newQuestionIds.add('Q4');assert.equal(context.nextReadyQuestion().id,'Q4','new questions take priority over older ready questions');
console.log('PASS next ready question order, wraparound, skipped questions, current-only and empty states');

for(const n of nodes){n.answer='Yes';n.ready=false;}
assert.equal(context.questionNavigation(),'', 'Completion belongs in the persistent interview status, not a buried footer');
context.pending=()=>null;nodes[3].answer=null;context.selected='Q4';
assert.equal(context.questionNavigation(),'','Only the selected unanswered question remains: no dead-end message');
context.selected='Q1';assert(context.questionNavigation().includes('Q4'),'Link to a blocked remaining question');
context.session.nodes=[];assert.equal(context.questionNavigation(),'','Empty tree is not complete');
console.log('PASS remaining-question navigation, persistent completion handoff and no dead-end footer');
