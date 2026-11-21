// Real rendered help, clipboard fallback, and receipt/publication across a live local server.
const {chromium}=require('playwright');
const {spawnSync,spawn}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),script=path.join(root,'scripts/grill_ui.py');
const shots=process.env.HELP_SHOTS;
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'grill-help-ui-')); let server,browser;
 const cli=(...args)=>{const r=spawnSync('python3',[script,...args],{encoding:'utf8'});assert.equal(r.status,0,r.stderr||r.stdout);return JSON.parse(r.stdout)};
 const state=()=>JSON.parse(fs.readFileSync(path.join(dir,'state.json')));
 const publish=(design,ack)=>{fs.writeFileSync(path.join(dir,'sample.json'),JSON.stringify(design));return cli('publish','--session-dir',dir,'--snapshot',path.join(dir,'sample.json'),'--expected-revision',String(design.revision-1),...(ack?['--ack',ack]:[]))};
 try {
 const sample=JSON.parse(fs.readFileSync(path.join(root,'examples/question-help.json')));
 delete sample.nodes[1].help; // Legacy session exercises on-demand recovery.
 fs.writeFileSync(path.join(dir,'legacy.json'),JSON.stringify(sample));
 publish(sample);
 fs.writeFileSync(path.join(dir,'connection.json'),JSON.stringify({provider:'codex',transport:'inbox',sessionId:'help-test'}));
 server=spawn('python3',[script,'serve','--session-dir',dir]);
 const url=await new Promise((resolve,reject)=>{let out='';server.stdout.on('data',b=>{out+=b;if(out.includes('\n'))resolve(JSON.parse(out.split('\n')[0]).url)});server.on('exit',c=>reject(Error('Server exited '+c)))});
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
 const page=await browser.newPage({viewport:{width:900,height:1080},permissions:['clipboard-read','clipboard-write']});
 page.setDefaultTimeout(7000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const selectQuestion=async id=>{if(await page.locator("#closePanel").isVisible())await page.locator("#closePanel").click();await page.locator("#fit").click();await page.locator(`[data-node="${id}"]`).click()};
 const shot=async name=>{if(shots){fs.mkdirSync(shots,{recursive:true});await page.screenshot({path:path.join(shots,name+'.png')});if(await page.locator('#questionHelpBody').count())await page.locator('#questionHelpBody').screenshot({path:path.join(shots,name+'-help.png')})}};
 await page.goto(url);await selectQuestion('Q1');
 await page.evaluate(()=>document.documentElement.style.setProperty('--sidebar-width','660px'));
 await shot('collapsed');
 await page.locator('#helpSimple').click();
 assert.equal(await page.locator('#helpEli15').innerText(),'ELI-15 (really simple)');
 assert.equal(await page.locator('#helpEli18').innerText(),'ELI-18');
 assert.equal(await page.locator('.question-details').innerText(),sample.nodes[0].question);
 assert.equal(state().events.length,0,'Prepared help opens without asking the agent');
 await shot('eli15');
 await page.locator('#helpEli18').click();assert.equal(await page.locator('#helpEli18').getAttribute('aria-pressed'),'true');await shot('eli18');
 await page.locator('#helpClose').click();assert.equal(await page.locator('#helpSimple').evaluate(e=>e===document.activeElement),true);
 await page.locator('#customTab').click();await page.locator('#draft').fill('Do not lose this unfinished answer.');
 await page.locator('#helpWalk').click();
 assert.equal(await page.locator('#helpPrevious').isDisabled(),true);await shot('walk-start');
 await page.locator('#helpNext').click();assert.equal(await page.locator('.help-visual-included').count(),2);
 await page.locator('#helpNext').click();assert.equal(await page.locator('.help-visual-excluded').count(),1);await shot('walk-boundary');
 await page.locator('#helpPrevious').click();assert.match(await page.locator('.help-step-heading').innerText(),/Step 2 of 4/);
 await page.locator('#helpNext').click();await page.locator('#helpNext').click();await page.locator('#helpNext').click();
 assert.equal(await page.locator('#questionHelpBody').count(),0);assert.equal(await page.locator('#draft').inputValue(),'Do not lose this unfinished answer.');
 assert.equal(await page.locator('#draft').evaluate(e=>e===document.activeElement),true);
 assert.equal(state().session.nodes[0].answer,null);
 // Returning to help retains level, original text, and draft on mobile too.
 await page.locator('#helpSimple').click();await page.keyboard.press('Escape');assert.equal(await page.locator('#questionHelpBody').count(),0);
 await page.locator('#helpSimple').click();await page.setViewportSize({width:390,height:900});await page.emulateMedia({colorScheme:'dark'});await page.locator('#helpSimple').scrollIntoViewIfNeeded();await shot('mobile-dark');
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 assert.equal(await page.locator('#questionHelpBody').evaluate(e=>e.scrollWidth>e.clientWidth),false);
 await page.setViewportSize({width:900,height:1080});await page.emulateMedia({colorScheme:'light'});
 await selectQuestion('Q2');await page.locator('#helpSimple').click();
 await page.getByRole('button',{name:'Copy request for agent'}).waitFor();
 await page.waitForFunction(()=>document.querySelector('#questionHelp .help-empty h4')?.textContent !== 'Requesting help…');
 await page.getByRole('button',{name:'Copy request for agent'}).click();
 assert.match(await page.evaluate(()=>navigator.clipboard.readText()),/ELI-15 \(really simple\).*ELI-18/);
 assert.match(await page.evaluate(()=>navigator.clipboard.readText()),/Explain import failures/);
 await shot('offline-help');
 const pending=state().events.find(e=>e.kind==='help');assert(pending);assert.equal(state().session.revision,1);
 fs.writeFileSync(path.join(dir,'presence.json'),JSON.stringify({at:Date.now()/1000}));
 await page.waitForFunction(()=>document.querySelector('#presenceLabel').textContent==='Waiting for agent');
 cli('receive','--session-dir',dir,'--event',pending.id);
 await page.waitForFunction(()=>document.querySelector('#presenceLabel').textContent==='Explaining');await shot('preparing');
 // Switching modes while a request is pending must not enqueue twice.
 await page.locator('#helpWalk').click();assert.equal(state().events.length,1);
 await page.locator('#customTab').click();await page.locator('#draft').fill('A separate draft during generation.');
 let next=state().session; next.revision++;
 const node=next.nodes[1];node.help=JSON.parse(JSON.stringify(sample.nodes[0].help));
 Object.assign(node.help,{basedOnRevision:next.revision,sourceQuestion:node.question,sourceRecommendation:node.agentRecommendationSummary+'\n\n'+node.agentRecommendation});
 node.help.eli15={title:'Show which link broke',paragraphs:['Imagine a checklist points to a missing file. The message tells you which link to fix.'],decision:'Should import errors name the failed link?'};
 node.help.eli18={title:'Identify the failing reference',paragraphs:['Include the source file and linked target in the error message.'],decision:'Should the message identify the reference that failed?'};
 node.help.walkthrough={title:'Illustrative example: a missing checklist',steps:[{title:'A skill links to a missing file',paragraphs:['The import stops. No incomplete skill is installed.']},{title:'The message identifies the problem',paragraphs:['The author can fix the link and try again.']}]};
 publish(next,pending.id);
 await page.waitForFunction(()=>document.querySelector('.help-step-heading')?.textContent.includes('missing checklist'));
 assert.equal(await page.locator('#draft').inputValue(),'A separate draft during generation.');
 assert.equal(await page.locator('#draft').evaluate(e=>e===document.activeElement),true);
 assert.equal(state().session.nodes[1].answer,null);assert(state().acknowledged.includes(pending.id));
 await page.locator('#helpShortVersion').click();assert.match(await page.locator('.help-explanation').innerText(),/Show which link broke/);
 // Unrelated publications preserve ready help; matching question changes invalidate it.
 next=state().session;next.revision++;next.nodes[1].notes='Unrelated supporting context';publish(next);
 await page.waitForFunction(()=>session.revision===3);
 await selectQuestion('Q1');assert.equal(await page.locator('#helpEli18').count(),1);
 assert.equal(await page.locator('#draft').inputValue(),'Do not lose this unfinished answer.');
 next=state().session;next.revision++;next.nodes[0].question='Should linked documents stay inside the skill folder?';publish(next);
 await page.waitForFunction(()=>document.querySelector('.question-details')?.textContent==='Should linked documents stay inside the skill folder?');
 assert.equal(await page.locator('#questionHelpBody').count(),0,'Changing the question resets the old help view');
 await page.locator('#helpSimple').click();assert.equal(await page.locator('.help-explanation').count(),0,'Never show an explanation for a different question');
 // Standalone keeps prepared help usable; missing help has a manual copy fallback.
 const standalone=path.join(dir,'standalone.html');cli('render','--snapshot',path.join(dir,'legacy.json'),'--output',standalone);
 await page.goto('file://'+standalone);await selectQuestion('Q2');await page.locator('#helpSimple').click();
 await page.evaluate(()=>{navigator.clipboard.writeText=()=>Promise.reject(Error('Denied'))});await page.locator('#copyHelpRequest').click();
 await page.getByRole('dialog',{name:'Copy help request'}).waitFor();assert.match(await page.locator('#copyText').inputValue(),/Current design:/);
 // The default example has instant help for every question, with no agent requests.
 cli('render','--require-help','--snapshot',path.join(root,'examples/question-help.json'),'--output',standalone);
 await page.goto('about:blank');await page.goto('file://'+standalone);
 for(const id of ['Q1','Q2']) {
  await selectQuestion(id);await page.locator('#helpSimple').click();
  assert.equal(await page.locator('#helpEli15').count(),1);
  await page.locator('#helpEli18').click();assert.equal(await page.locator('.help-explanation').count(),1);
  await page.locator('#helpShowExample').click();assert.equal(await page.locator('#helpNext').count(),1);
  assert.equal(await page.locator('#copyHelpRequest').count(),0);
 }
 assert.deepEqual(errors,[]);
 console.log('PASS ready explanations, walkthrough, keyboard/mobile, exact labels, draft preservation, offline copy, live receipt/publication, stale help, and standalone fallback');
 } finally {await browser?.close();server?.kill();fs.rmSync(dir,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});
