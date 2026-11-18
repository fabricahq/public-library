const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../assets/canvas.html'),'utf8');
let clock=0, sequence=0;
const timers=new Map(), announcement={textContent:''};
const context={WeakMap,$:()=>announcement,
 setTimeout:(callback,delay)=>{const id=++sequence;timers.set(id,{callback,at:clock+delay});return id;},
 clearTimeout:id=>timers.delete(id)};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('      const copyFeedbackTimers'),source.indexOf('      async function copyReply')),context);
function advance(ms){clock+=ms;for(const [id,t] of [...timers])if(t.at<=clock){timers.delete(id);t.callback();}}
function button(label=null){
 const icon={innerHTML:'original-copy-path'}, classes=new Set(),attrs=new Map(label?[['aria-label',label]]:[]);
 return {icon,classes,isConnected:true,textContent:'Copy this message',querySelector:()=>icon,
 getAttribute:key=>attrs.get(key)??null,setAttribute:(key,value)=>attrs.set(key,value),removeAttribute:key=>attrs.delete(key),
 classList:{add:key=>classes.add(key),remove:key=>classes.delete(key)}};
}
const a=button(), b=button('Copy file path');
context.showCopySuccess(a);
assert(a.classes.has('copy-success'));assert.notEqual(a.icon.innerHTML,'original-copy-path');
assert.equal(a.textContent,'Copy this message');assert.equal(a.getAttribute('aria-label'),'Copy this message: Copied');
assert.equal(announcement.textContent,'Copied to clipboard.');
advance(1000);context.showCopySuccess(a);context.showCopySuccess(b);
advance(1000);assert(a.classes.has('copy-success'),'repeated click restarts two-second confirmation');
advance(1000);
for(const el of [a,b]){assert(!el.classes.has('copy-success'));assert.equal(el.icon.innerHTML,'original-copy-path');}
assert.equal(a.getAttribute('aria-label'),null);assert.equal(b.getAttribute('aria-label'),'Copy file path');
context.showCopySuccess(a);a.isConnected=false;advance(2000);assert.equal(timers.size,0,'removed controls release timers');
context.showCopySuccess(null);
console.log('PASS local copy confirmation, unchanged labels, two-second reset, repeated clicks, accessibility and detached controls');
