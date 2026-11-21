const {chromium}=require('playwright');
const {spawn,spawnSync}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),script=path.join(root,'scripts/grill_ui.py');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'grill-confidence-'));let server,browser;
 const assessment=level=>({level,reason:'An illustrative assessment.',evidence:'Example specification.'});
 const fixture={id:'confidence-test',schemaVersion:1,title:'Confidence test',revision:1,nodes:[
  ['Q1','low','low'],['Q2','high','low'],['Q3','low','high'],['Q4','medium','medium'],['Q5','high','high'],['Q6',null,null]
 ].map(([id,c,r])=>({id,parentId:null,title:'Decision '+id,question:'Should we choose '+id+'?',answer:null,dependsOn:[],agentRecommendationSummary:'Yes.',agentRecommendation:'A test recommendation.',...(c?{contextConfidence:assessment(c),recommendationConfidence:assessment(r)}:{})}))};
 const file=path.join(dir,'snapshot.json');fs.writeFileSync(file,JSON.stringify(fixture));
 try{
  const published=spawnSync('python3',[script,'publish','--session-dir',dir,'--snapshot',file,'--expected-revision','0'],{encoding:'utf8'});assert.equal(published.status,0,published.stderr+published.stdout);
  server=spawn('python3',[script,'serve','--session-dir',dir]);
  const url=await new Promise((resolve,reject)=>{let out='';server.stdout.on('data',c=>{out+=c;if(out.includes('\n'))resolve(JSON.parse(out.split('\n')[0]).url)});server.on('exit',c=>reject(Error('Server exited '+c)))});
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
  const page=await browser.newPage({viewport:{width:1500,height:1000}});page.setDefaultTimeout(7000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);
  const count=async n=>{await page.waitForFunction(n=>document.querySelector('#confidenceCount strong').textContent===String(n),n)};
  await count(6);assert(await page.locator('#resetConfidence').isDisabled());
  await page.locator('#matrixView').click();assert(await page.locator('#canvas').isHidden());assert.equal(await page.locator('.matrix-decision').count(),6);
  assert.equal(await page.locator('.confidence-unassessed .matrix-decision').count(),1);
  await page.locator('[data-confidence-node="Q1"]').click();await page.locator('#customTab').click();await page.locator('#draft').fill('Preserve my reasoning.');
  await page.locator('#confidenceGroups').click();
  await page.locator('#noConfidenceGroups').click();
  await page.locator('[data-pair="Low,Low"]').click();
  await page.locator('[data-pair="High,Low"]').click();
  await page.keyboard.press('Escape');assert(await page.locator('#confidenceGroups').evaluate(e=>e===document.activeElement));assert(await page.locator('#panel').isVisible());
  await count(2);assert.equal(await page.locator('#draft').inputValue(),'Preserve my reasoning.');
  const excluded=page.locator('.confidence-cell.excluded');assert.equal(await excluded.count(),7);
  assert.equal(await excluded.locator('button,.confidence-cell-top,.cell-count,.cell-scroll-hint').count(),0);
  assert.deepEqual(await excluded.allTextContents(),Array(7).fill('Filtered out'));
  assert.equal(await page.locator('.confidence-cell:not(.excluded) .matrix-nothing').count(),0);
  await page.locator('#treeView').click();assert.equal(await page.locator('#tree foreignObject.confidence-muted').count(),4);await count(2);
  const transform=await page.locator('#tree').getAttribute('transform');await page.locator('#matrixView').click();await page.locator('#treeView').click();assert.equal(await page.locator('#tree').getAttribute('transform'),transform);
  await page.locator('#resetConfidence').click();await count(6);assert.equal(await page.locator('#draft').inputValue(),'Preserve my reasoning.');
  await page.locator('#send').click();await page.waitForFunction(()=>document.querySelector('#panel').innerText.includes('Preserve my reasoning.')&&!document.querySelector('#draft'));
  let state=JSON.parse(fs.readFileSync(path.join(dir,'state.json')));assert.equal(state.session.nodes[0].answer,'Preserve my reasoning.');assert.equal(state.session.nodes[0].contextConfidence.level,'low');
  await page.locator('#matrixView').click();await page.locator('#jumpUncertain').click();await count(1);await page.getByRole('button',{name:'Clear focus',exact:true}).click();await count(6);assert.equal(await excluded.count(),0);assert.equal(await page.locator('[data-confidence-cell]').count(),9);assert.equal(await page.locator('.matrix-nothing', {hasText:'No questions in this group'}).count(),4);
  await page.locator('#confidenceGroups').click();await page.locator('#noConfidenceGroups').click();await page.locator('#finishConfidenceGroups').click();await count(0);assert(await page.locator('#nextQuestion').isDisabled());assert.equal(await page.locator('.matrix-decision').count(),0);
  await page.locator('#resetConfidence').click();await count(6);
  // Live publications move a question between cells without changing its answer or review history.
  const before=state.answerState;state.session.revision++;state.session.nodes[0].contextConfidence=assessment('high');fs.writeFileSync(file,JSON.stringify(state.session));
  const publish=spawnSync('python3',[script,'publish','--session-dir',dir,'--snapshot',file,'--expected-revision',String(state.session.revision-1)],{encoding:'utf8'});assert.equal(publish.status,0,publish.stderr+publish.stdout);
  await page.getByRole('region',{name:'High context confidence, Low recommendation confidence',exact:true}).locator('[data-confidence-node="Q1"]').waitFor();
  state=JSON.parse(fs.readFileSync(path.join(dir,'state.json')));assert.deepEqual(state.answerState,before);assert.equal(state.session.nodes[0].answer,'Preserve my reasoning.');
  await page.locator('#confidenceGroups').click();await page.locator('#noConfidenceGroups').click();await page.locator('#includeUnassessed').check();await page.locator('#finishConfidenceGroups').click();await count(1);assert.equal(await page.locator('.confidence-unassessed .matrix-decision').count(),1);
  await page.locator('#resetConfidence').click();
  await page.locator('#menuButton').click();await page.locator('#openSettings').click();await page.locator('[data-settings-section="appearance"]').click();await page.locator('#appearance').selectOption('dark');await page.keyboard.press('Escape');assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
  await page.setViewportSize({width:390,height:844});await page.locator('#closePanel').click();assert(await page.locator('#matrixView').isVisible());
  assert(await page.locator('.confidence-toolbar').evaluate(e=>e.getBoundingClientRect().right<=innerWidth));
  assert.deepEqual(errors,[]);
  console.log('PASS confidence combinations, missing assessments, view switching, drafts, real save, focus reset, empty selection, live publication, camera preservation, dark and mobile');
 }finally{await browser?.close();server?.kill();fs.rmSync(dir,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});
