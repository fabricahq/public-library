const {chromium}=require('playwright');
const {spawn,spawnSync}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),script=path.join(root,'scripts/grill_ui.py');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'grill-markdown-tables-'));let server,browser;
 const cli=(...args)=>{const p=spawnSync('python3',[script,...args],{encoding:'utf8'});assert.equal(p.status,0,p.stderr);return JSON.parse(p.stdout)};
 try{
  cli('publish','--session-dir',dir,'--snapshot',path.join(root,'examples/design-context.json'),'--expected-revision','0');
  const file=path.join(dir,'opening-spec.md');
  const content='# Opening states\n\n| State | What the user sees | Writes |\n| --- | --- | --- |\n| No cache, validation pending | Existing loading presentation; no invented or fallback document content | Disabled |\n| Cached preview, validation pending less than 2 seconds | Cached document, without the fetching bubble | Disabled |\n| Validation succeeds | Current server document initializes the editing session; fetching message disappears | Enabled only if existing permissions, lifecycle and connection allow |\n| Transient failure or offline | Available cached preview plus clear error/retry state | Disabled until successful validation |\n| Missing required draft | Distinct data-integrity failure with diagnostic context and retry | Disabled |\n\nA new editing session begins when the selected artifact changes.\n\n## Alignment and formatting\n\nName | Detail | Count\n:--- | :---: | ---:\n**Bold** | `code` and a pipe \\| here | 42\n';
  fs.writeFileSync(file,content);cli('artifact','--session-dir',dir,'--file',file,'--title','Opening specification');
  server=spawn('python3',[script,'serve','--session-dir',dir]);
  const url=await new Promise((resolve,reject)=>{let out='';server.stdout.on('data',c=>{out+=c;if(out.includes('\n'))resolve(JSON.parse(out.split('\n')[0]).url)});server.on('exit',c=>reject(Error('Server exited '+c)))});
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
  const page=await browser.newPage({viewport:{width:1280,height:900}});page.setDefaultTimeout(5000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const shot=async name=>{if(process.env.TABLE_SHOTS)await page.screenshot({path:path.join(process.env.TABLE_SHOTS,name+'.png')})};
  await page.goto(url);await page.locator('#artifactsButton').click();
  await page.getByRole('button',{name:'Open opening-spec.md on canvas',exact:true}).click();
  await page.locator('#closeArtifacts').click();
  const win=page.locator('.artifact-window').filter({has:page.getByRole('button',{name:'opening-spec.md',exact:true})});await win.waitFor();
  await win.getByRole('button',{name:'Maximize document',exact:true}).click();
  if(process.env.TABLE_BASELINE){assert.equal(await win.locator('table').count(),0);assert((await win.locator('.artifact-body').textContent()).includes('| State |'));await shot('before');console.log('REPRODUCED: table Markdown appears as raw pipe text');return;}
  assert.equal(await win.locator('table').count(),2);
  const table=win.locator('table').first();
  assert.deepEqual(await table.locator('th').allTextContents(),['State','What the user sees','Writes']);
  assert.equal(await table.locator('tbody tr').count(),5);
  await shot('desktop');
  await win.getByRole('button',{name:'Zoom in document',exact:true}).click();await win.getByRole('button',{name:'Zoom in document',exact:true}).click();
  await shot('zoomed');
  await page.setViewportSize({width:1960,height:730});await shot('wide');await page.setViewportSize({width:1280,height:900});
  await win.getByRole('button',{name:'Reset document zoom to 100%',exact:true}).click();
  await page.emulateMedia({colorScheme:'dark'});await shot('dark');await page.emulateMedia({colorScheme:'light'});
  await win.getByRole('button',{name:'Source',exact:true}).click();assert((await win.locator('.markdown-source').textContent()).includes('| State |'));assert.equal(await win.locator('table').count(),0);
  await win.getByRole('button',{name:'Rendered',exact:true}).click();
  await page.setViewportSize({width:375,height:812});
  await page.waitForFunction(()=>document.querySelector('#documentFullscreen .artifact-window')?.getBoundingClientRect().width===innerWidth);
  await shot('mobile');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert(await win.locator('.markdown-table').first().evaluate(el=>{el.scrollLeft=200;return el.scrollLeft>0}),'Wide table must scroll locally');
  assert.deepEqual(errors,[]);
  console.log('PASS Markdown tables: rendered/source, zoom, themes and mobile overflow');

 }finally{await browser?.close();server?.kill();fs.rmSync(dir,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});
