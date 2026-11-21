// Optional E2E check: install Playwright and its Chromium/WebKit browsers, then run with Node.
// PINCH_BROWSERS can select one engine; *_EXECUTABLE_PATH can use an existing installation.
const {chromium,webkit}=require('playwright');
const {spawnSync,spawn}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),script=path.join(root,'scripts/grill_ui.py');
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'grill-pinch-'));
const run=(...args)=>{const r=spawnSync('python3',[script,...args],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);};
(async()=>{
 let server;
 try {
  run('publish','--session-dir',directory,'--snapshot',path.join(root,'examples/design-context.json'),'--expected-revision','0');
  const glossary=path.join(directory,'CONTEXT.md');
  fs.writeFileSync(glossary,'# Test glossary\n\n'+Array.from({length:60},(_,i)=>`**Term ${i+1}**: A definition long enough to exercise native document scrolling.\n\n`).join(''));
  run('artifact','--session-dir',directory,'--file',glossary);
  server=spawn('python3',[script,'serve','--session-dir',directory],{stdio:['ignore','pipe','pipe']});
  const url=await new Promise((resolve,reject)=>{let text='';server.stdout.on('data',chunk=>{text+=chunk;if(text.includes('\n'))resolve(JSON.parse(text.split('\n')[0]).url);});server.on('exit',code=>reject(Error('Server exited: '+code)));});
  for(const name of (process.env.PINCH_BROWSERS || "chromium,webkit").split(",")) {
   const type={chromium,webkit}[name];
   const browser=await type.launch({headless:true,timeout:15000,executablePath:process.env[name.toUpperCase()+"_EXECUTABLE_PATH"]});
   try {
    const page=await browser.newPage({viewport:{width:1280,height:900}});
    page.setDefaultTimeout(10000);
    await page.goto(url);
    await page.locator('#artifactsButton').click();
    await page.getByRole('button',{name:'Open Constraints on canvas',exact:true}).click();
    const doc=page.locator('.artifact-window').filter({has:page.getByRole('button',{name:'Constraints',exact:true})});
    await doc.waitFor();
    const result=await page.evaluate(()=>{
     const results=[];
     const scale=()=>new DOMMatrix(getComputedStyle(document.querySelector('#artifactWorld')).transform).a;
     const targets=['#canvas','.artifact-body','.artifact-titlebar','.artifact-resize[data-edge="se"]'];
     for(const selector of targets){
      const target=document.querySelector(selector),rect=target.getBoundingClientRect();
      const point={clientX:rect.x+rect.width/2,clientY:rect.y+rect.height/2};
      for(const deltaY of [-20,20]){
       const before=scale(),event=new WheelEvent('wheel',{bubbles:true,cancelable:true,ctrlKey:true,deltaY,...point});
       target.dispatchEvent(event);
       results.push({selector,type:'wheel',prevented:event.defaultPrevented,changed:deltaY<0?scale()>before:scale()<before});
      }
      const before=scale();
      for(const [type,s] of [['gesturestart',1],['gesturechange',1.2],['gesturechange',.8],['gestureend',.8]]){
       const prior=scale(),event=new Event(type,{bubbles:true,cancelable:true});Object.assign(event,point,{scale:s});target.dispatchEvent(event);
       results.push({selector,type,prevented:event.defaultPrevented,changed:type!=='gesturechange'||(s>1?scale()>prior:scale()<prior)});
      }
      results.push({selector,type:'gesture-total',prevented:true,changed:Math.abs(scale()/before-.8)<1e-8});
     }
     const body=document.querySelector('.artifact-body'),before=scale();
     const scroll=new WheelEvent('wheel',{bubbles:true,cancelable:true,deltaY:50});body.dispatchEvent(scroll);
     results.push({selector:'document scroll',type:'wheel',prevented:!scroll.defaultPrevented,changed:scale()===before});
     return results;
    });
    assert.deepEqual(result.filter(r=>!r.prevented||!r.changed),[],name+': pinch must zoom the workspace and cancel browser zoom; ordinary document scroll must remain native');
    // Trusted browser wheel events must still scroll the file, without panning the tree.
    await page.reload();
    await page.locator('#artifactsButton').click();
    await page.getByRole('button',{name:'Open CONTEXT.md on canvas',exact:true}).click();
    const body=page.locator('.artifact-window').filter({has:page.getByRole('button',{name:'CONTEXT.md',exact:true})}).locator('.artifact-body');
    await body.hover();
    const zoomBefore=await page.locator('#artifactWorld').getAttribute('style');
    await page.keyboard.down('Control');
    await page.mouse.wheel(0,-40);
    await page.keyboard.up('Control');
    await page.waitForFunction(previous=>document.querySelector('#artifactWorld').getAttribute('style')!==previous,zoomBefore);
    assert.equal(await page.evaluate(()=>visualViewport.scale),1,'Pinch must not magnify the browser page');
    await body.hover();const before=await page.locator('#artifactWorld').getAttribute('style');
    await page.mouse.wheel(0,180);
    await page.waitForFunction(()=>Array.from(document.querySelectorAll('.artifact-body')).some(e=>e.scrollTop>0));
    assert.equal(await page.locator('#artifactWorld').getAttribute('style'),before,'Document scrolling must not pan the tree');
    console.log('PASS '+name+': pinch over canvas, document, title and resize handle; native document scrolling');
   } finally {await browser.close();}
  }
 } finally {if(server)server.kill();fs.rmSync(directory,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
