const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const session=JSON.parse(fs.readFileSync(path.join(__dirname,'../examples/question-help.json')));
const node=session.nodes[0];node.parentId='Q2';session.revision=5;
const context={session,answerState:{Q1:{changedAt:1},Q2:{changedAt:1}},get:id=>session.nodes.find(n=>n.id===id),
 deps:n=>[n.parentId,...(n.dependsOn||[])].filter(Boolean),recommendationText:n=>[n.agentRecommendationSummary,n.agentRecommendation].filter(Boolean).join('\n\n')};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../assets/question-help.js'),'utf8'),context);
assert.equal(context.currentQuestionHelp(node),node.help,'Unrelated revisions retain current help');
context.answerState.Q2.changedAt=4;
assert.equal(context.currentQuestionHelp(node),null,'A prerequisite change hides old help');
node.help.basedOnRevision=5;
assert.equal(context.currentQuestionHelp(node),node.help,'Regeneration restores current help');
node.agentRecommendation='New recommendation';
assert.equal(context.currentQuestionHelp(node),null,'Recommendation changes require new help');
node.help.sourceRecommendation=context.recommendationText(node);
assert.equal(context.currentQuestionHelp(node),node.help);
node.question='New question';assert.equal(context.currentQuestionHelp(node),null);
node.help.sourceQuestion=node.question;node.help.basedOnRevision=6;
assert.equal(context.currentQuestionHelp(node),null,'Future help is not current');
console.log('PASS prepared help freshness across unrelated updates, prerequisite changes, recommendation changes and regeneration');
