const fs=require('node:fs'), path=require('node:path'), vm=require('node:vm'), assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../assets/canvas.html'),'utf8');
const helper=source.slice(source.indexOf('      async function copyArtifactPath'),source.indexOf('      function createArtifactWindow'));
let copied=[],fallback=[],messages=[];
const context={artifactFiles:[{id:'glossary',path:'/project/CONTEXT.md'}],navigator:{clipboard:{writeText:async value=>copied.push(value)}},showCopySuccess:button=>messages.push(button),openCopy:(value,options)=>fallback.push({value,options}),$:()=>({open:false}),setTimeout,clearTimeout};
vm.createContext(context);vm.runInContext(helper,context);
(async()=>{
 await context.copyArtifactPath('glossary');assert.equal(copied[0],'/project/CONTEXT.md');assert.equal(fallback.length,0);assert.equal(messages.length,1);
 context.artifactFiles[0].path='/moved/CONTEXT.md';await context.copyArtifactPath('glossary');assert.equal(copied[1],'/moved/CONTEXT.md');
 context.navigator.clipboard.writeText=async()=>{throw Error('denied')};await context.copyArtifactPath('glossary');assert.equal(fallback[0].value,'/moved/CONTEXT.md');assert.equal(fallback[0].options.filePath,true);
 context.navigator.clipboard.writeText=()=>new Promise(()=>{});await context.copyArtifactPath('glossary');assert.equal(fallback.length,2,'pending permission must reach a manual fallback');
 await context.copyArtifactPath('removed');assert.equal(fallback.length,2);assert.equal(messages.length,2,'failed copies must not claim success');
 console.log('PASS current file path, clipboard success, rejection and pending-permission fallback');
})().catch(error=>{console.error(error);process.exitCode=1});
