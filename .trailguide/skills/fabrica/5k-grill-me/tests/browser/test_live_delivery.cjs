// Isolated live transport E2E. Uses a deterministic agent receipt/publication, not a model.
const {chromium}=require('playwright');
const {spawnSync,spawn}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),script=path.join(root,'scripts/grill_ui.py');
(async()=>{
 let browser,server,listener;
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'grill-live-browser-'));
 const cli=(...args)=>{const p=spawnSync('python3',[script,...args],{encoding:'utf8'});assert.equal(p.status,0,p.stderr);return JSON.parse(p.stdout)};
 try {
  cli('publish','--session-dir',dir,'--snapshot',path.join(root,'examples/design-context.json'),'--expected-revision','0');
  fs.writeFileSync(path.join(dir,'connection.json'),JSON.stringify({provider:'codex',transport:'inbox'}));
  server=spawn('python3',[script,'serve','--session-dir',dir]);
  const url=await new Promise((resolve,reject)=>{let output='';server.stdout.on('data',chunk=>{output+=chunk;if(output.includes('\n'))resolve(JSON.parse(output.split('\n')[0]).url)});server.on('exit',code=>reject(Error('Server exited: '+code)))});
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
  const page=await browser.newPage({viewport:{width:1100,height:1000}});
  page.setDefaultTimeout(5000);
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const shot=async name=>{if(process.env.DELIVERY_SHOTS)await page.screenshot({path:path.join(process.env.DELIVERY_SHOTS,`delivery-${name}.png`)})};
  await page.goto(url);await page.locator('[data-node="Q2"]').click();
  await page.locator('#customTab').click();
  await page.locator('#draft').fill('Include only decision-relevant examples.');await page.locator('#send').click();
  await page.locator('#copySavedReply').waitFor();
  await shot('offline');
  assert(!(await page.locator('.answer-delivery').count()) || !(await page.locator('.answer-delivery').innerText()).includes('Received'));
  const start=performance.now();
  listener=spawn('python3',[script,'wait','--session-dir',dir,'--timeout','20']);
  const event=await new Promise((resolve,reject)=>{let output='';listener.stdout.on('data',chunk=>output+=chunk);listener.on('exit',code=>code===0?resolve(JSON.parse(output).event):reject(Error('Wait failed')))});
  await page.getByText('Preparing your next question… This page updates automatically.',{exact:true}).waitFor();
  const receiptMs=performance.now()-start;
  assert(receiptMs<1500,`Receipt took ${receiptMs} ms to render`);
  assert.equal(await page.locator('#copySavedReply').count(),0);
  await shot('received-desktop');
  await page.setViewportSize({width:540,height:1000});await shot('received-narrow');
  const state=JSON.parse(fs.readFileSync(path.join(dir,'state.json')));
  const next=state.session;next.revision++;
  next.nodes.push({id:'Q3',parentId:'Q2',title:'Choose the first example',question:'Which decision should the first example help you make?',answer:null,dependsOn:[]});
  const file=path.join(dir,'next.json');fs.writeFileSync(file,JSON.stringify(next));
  const published=performance.now();
  cli('publish','--session-dir',dir,'--snapshot',file,'--expected-revision',String(next.revision-1),'--ack',event.id);
  await page.getByRole('heading',{name:'Choose the first example',exact:true}).waitFor();
  const publishMs=performance.now()-published;
  assert(publishMs<1500,`Publication took ${publishMs} ms to render`);
  await shot('followup-narrow');
  assert.equal(await page.locator('#draft').inputValue(),'');
  assert.deepEqual(errors,[]);
  console.log(`PASS offline fallback, confirmed receipt, streamed follow-up and automatic selection; receipt ${Math.round(receiptMs)} ms, publication ${Math.round(publishMs)} ms`);
 } finally {await browser?.close();listener?.kill();server?.kill();fs.rmSync(dir,{recursive:true,force:true})}
})().catch(error=>{console.error(error);process.exitCode=1});
