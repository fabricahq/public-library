const {chromium}=require('playwright');
const {spawn,spawnSync}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),script=path.join(root,'scripts/grill_ui.py');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'grill-about-'));let server,browser;
 try{
  const published=spawnSync('python3',[script,'publish','--session-dir',dir,'--snapshot',path.join(root,'examples/design-context.json'),'--expected-revision','0'],{encoding:'utf8'});
  assert.equal(published.status,0,published.stderr);
  server=spawn('python3',[script,'serve','--session-dir',dir]);
  const url=await new Promise((resolve,reject)=>{let out='';server.stdout.on('data',c=>{out+=c;if(out.includes('\n'))resolve(JSON.parse(out.split('\n')[0]).url)});server.on('exit',c=>reject(Error('Server exited '+c)))});
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
  const page=await browser.newPage({viewport:{width:1100,height:900}});page.setDefaultTimeout(5000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const shot=async name=>{if(process.env.ABOUT_SHOTS)await page.screenshot({path:path.join(process.env.ABOUT_SHOTS,name+'.png')})};
  await page.goto(url);await page.locator('[data-node="Q2"]').click();
  await page.locator('#customTab').click();await page.locator('#draft').fill('Keep this draft.');
  await page.locator('#menuButton').click();await shot('menu-light');
  await page.getByRole('button',{name:'About 5K Grill Me',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'5K Grill Me',exact:true});await dialog.waitFor();
  assert(await page.locator('#menu').isHidden());
  assert((await dialog.innerText()).includes('5K Grill Me is a skill by Fabrica that brings Matt Pocock'));
  assert((await dialog.innerText()).includes('Matt Pocock'));
  assert((await dialog.innerText()).includes('Fred Brooks'));
  assert.equal(await dialog.getByRole('link',{name:'grill-me',exact:true}).getAttribute('href'),'https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md');
  assert.equal(await dialog.getByRole('link',{name:'Fabrica',exact:true}).getAttribute('href'),'https://fabricahq.com');
  await shot('about-light');
  for(let i=0;i<8;i++){
   await page.keyboard.press('Tab');
   assert(await dialog.evaluate(e=>e.contains(document.activeElement)||document.activeElement===document.body),'Tab must not focus background controls; native dialogs may yield focus to browser chrome');
  }
  await page.locator('#menuButton').evaluate(e=>e.focus());
  assert(!(await page.locator('#menuButton').evaluate(e=>e===document.activeElement)),'Background controls are inert while the modal is open');
  await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
  assert(await page.locator('#panel').isVisible(),'Escape must not close the selected question');
  assert.equal(await page.locator('#draft').inputValue(),'Keep this draft.');
  await page.waitForFunction(()=>document.activeElement===document.querySelector('#menuButton'));
  await page.locator('#menuButton').click();await page.locator('#openAbout').click();
  await page.emulateMedia({colorScheme:'dark'});await shot('about-dark');
  await page.locator('#closeAbout').click();assert.equal(await page.locator('#draft').inputValue(),'Keep this draft.');
  await page.emulateMedia({colorScheme:'light'});await page.setViewportSize({width:375,height:812});
  await page.locator('#menuButton').click();await shot('menu-narrow');await page.locator('#openAbout').click();
  await shot('about-narrow');
  assert(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),'Modal content must fit narrow screens');
  await page.locator('#closeAbout').click();
  await page.setViewportSize({width:667,height:375});
  await page.locator('#menuButton').click();await page.locator('#openAbout').click();
  assert.equal(await dialog.evaluate(e=>e.scrollTop),0,'A short viewport starts with the title visible');
  const bounds=await dialog.boundingBox(),close=await page.locator('#closeAbout').boundingBox();
  assert(close.y+close.height<bounds.y+bounds.height-15,'Close must stay fully visible with bottom spacing');
  await shot('about-short-top');
  await page.locator('.about-copy').evaluate(el=>el.scrollTop=el.scrollHeight);await shot('about-short');
  assert(await page.locator('#closeAbout').isVisible());
  await page.locator('#closeAbout').click();assert(await page.locator('#panel').isVisible());
  assert.deepEqual(errors,[]);
  console.log('PASS About credits, source link, modal focus, Escape/Close preserve draft, light/dark and narrow/short layouts');
 }finally{await browser?.close();server?.kill();fs.rmSync(dir,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});
