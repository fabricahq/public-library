const {chromium}=require('playwright');
const {spawnSync}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'grill-stale-'));let browser;
 try{
  const snapshot={id:'stale-draft',title:'Storage design',revision:1,nodes:[
   {id:'Q1',parentId:null,title:'Storage',question:'Where should data live?',answer:'Local files'},
   {id:'Q2',parentId:'Q1',title:'Backup',question:'How should backups work?',answer:null},
   {id:'Q3',parentId:null,title:'Support',question:'When should support be available?',answer:'Weekdays'}
  ]};
  fs.writeFileSync(path.join(dir,'input.json'),JSON.stringify(snapshot));
  const rendered=spawnSync('python3',[path.join(root,'scripts/grill_ui.py'),'render','--snapshot',path.join(dir,'input.json'),'--output',path.join(dir,'canvas.html')],{encoding:'utf8'});
  assert.equal(rendered.status,0,rendered.stderr);
  browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1280,height:900}});page.setDefaultTimeout(3000);
  await page.goto('file://'+path.join(dir,'canvas.html'));
  await page.locator('[data-node="Q2"]').click();await page.locator('#draft').fill('Use a local filesystem backup');await page.locator('#closePanel').click();
  await page.locator('[data-node="Q3"]').click();await page.locator('#editAnswer').click();await page.locator('#draft').fill('Every day');await page.locator('#send').click();await page.locator('.answer-body').filter({hasText:'Every day'}).waitFor();await page.locator('#closePanel').click();
  await page.locator('[data-node="Q2"]').click();await page.locator('#send').click();await page.locator('.answer-body').filter({hasText:'Use a local filesystem backup'}).waitFor();
  await page.locator('#editAnswer').click();await page.locator('#draft').fill('Use a versioned local filesystem backup');await page.locator('#closePanel').click();
  await page.locator('[data-node="Q1"]').click();await page.locator('#editAnswer').click();await page.locator('#draft').fill('Cloud only, no local files');await page.locator('#send').click();await page.locator('.answer-body').filter({hasText:'Cloud only'}).waitFor();await page.locator('#closePanel').click();
  await page.locator('[data-node="Q2"]').click();await page.locator('#send').click();
  assert(await page.locator('#toast').innerText().then(text=>text.includes('prerequisite changed')));
  assert.equal(await page.locator('#draft').inputValue(),'Use a versioned local filesystem backup');
  await page.locator('#refreshDraftContext').click();await page.locator('#draft').fill('Use a versioned cloud backup');await page.locator('#send').click();await page.locator('.answer-body').filter({hasText:'Use a versioned cloud backup'}).waitFor();
  console.log('PASS unrelated edits allow submission; changed prerequisites preserve drafts until explicit review');
 }finally{await browser?.close();fs.rmSync(dir,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1});
