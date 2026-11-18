const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/canvas.html'), 'utf8');
const start = source.indexOf('// Workspace wheel and pinch navigation.');
const events = source.slice(start < 0 ? source.indexOf('      $("canvas").addEventListener(\n        "wheel"') : start, source.indexOf('      $("zoomIn").onclick'));
const zoom = source.slice(source.indexOf('      function zoom('), source.indexOf('      function select('));
function harness(origin = {left:0,top:0}) {
 const handlers = {}, pan = {x:100,y:80,scale:1};
 const canvas = {addEventListener(name,fn,options) { assert.equal(options.passive,false);handlers[name]=fn; },getBoundingClientRect(){return {...origin,height:800,width:1000};},classList:{remove(){}}};
 new Function('$','pan','transform','available','innerHeight', 'let drag=null;'+zoom+events)(id=>{assert(['canvas','workspace'].includes(id));return canvas;},pan,()=>{},()=>({w:1000,h:800}),800);
 return {pan,fire(type,values={}) {assert(handlers[type], `Missing ${type} handler`);const e={deltaX:0,deltaY:0,deltaMode:0,ctrlKey:false,metaKey:false,clientX:400,clientY:300,scale:1,target:{closest:selector=>selector.includes("#canvas")},preventDefault(){this.prevented=true;},...values};handlers[type](e);assert.equal(Boolean(e.prevented),values.expectedPrevented!==false);return e;}};
}
const close = (a,b) => assert(Math.abs(a-b)<1e-9,`${a} != ${b}`);
let h=harness(); h.fire('wheel',{deltaX:25,deltaY:40});
assert.deepEqual(h.pan,{x:75,y:40,scale:1},'Two-finger scrolling must pan, not change zoom');
h.fire('wheel',{deltaY:2,deltaMode:1});close(h.pan.y,8);
h=harness();const wx=(400-h.pan.x)/h.pan.scale,wy=(300-h.pan.y)/h.pan.scale;
h.fire('wheel',{deltaY:-20,ctrlKey:true});assert(h.pan.scale>1);close((400-h.pan.x)/h.pan.scale,wx);close((300-h.pan.y)/h.pan.scale,wy);
h.fire('wheel',{deltaY:20,ctrlKey:true});close(h.pan.scale,1);
h=harness();h.fire('gesturestart');h.fire('gesturechange',{scale:1.5});close(h.pan.scale,1.5);
h.fire('wheel',{ctrlKey:true,deltaY:-20});close(h.pan.scale,1.5);
h.fire('gesturechange',{scale:1.2});close(h.pan.scale,1.2);h.fire('gestureend');
h.fire('wheel',{deltaY:40});close(h.pan.scale,1.2);
h=harness();h.fire('gesturestart');h.fire('gesturechange',{scale:0.5});close(h.pan.scale,0.5);h.fire('gesturechange',{scale:0.01});close(h.pan.scale,0.12);h.fire('gestureend');
console.log('PASS scroll pans; pinch zooms both ways at pointer; normalized deltas; WebKit cumulative gestures; no double zoom; zoom limits');

// The toolbar offsets the canvas: pinch must still anchor to canvas-local coordinates.
h=harness({left:0,top:76});
const anchoredY=(300-76-h.pan.y)/h.pan.scale;
h.fire('wheel',{deltaY:-20,ctrlKey:true});
close((300-76-h.pan.y)/h.pan.scale,anchoredY);
h=harness({left:0,top:76});
h.fire('gesturestart');h.fire('gesturechange',{scale:1.4});
close((300-76-h.pan.y)/h.pan.scale,anchoredY);
console.log('PASS pointer anchoring below the docked toolbar');

// Document pinch shares canvas zoom, but document scrolling remains native.
const documentTarget={closest:selector=>selector.includes('.artifact-window')};
h=harness({left:0,top:76});
h.fire('wheel',{target:documentTarget,deltaY:40,expectedPrevented:false});
assert.deepEqual(h.pan,{x:100,y:80,scale:1});
h.fire('wheel',{target:documentTarget,deltaY:-20,ctrlKey:true});
assert(h.pan.scale>1);
close((300-76-h.pan.y)/h.pan.scale,anchoredY);
h=harness();h.fire('gesturestart',{target:documentTarget});
h.fire('gesturechange',{scale:1.4});close(h.pan.scale,1.4);
h.fire('wheel',{target:documentTarget,deltaY:-20,ctrlKey:true});close(h.pan.scale,1.4);
h.fire('gestureend');
const outsideTarget={closest:()=>null};
h.fire('wheel',{target:outsideTarget,ctrlKey:true,deltaY:-20,expectedPrevented:false});
h.fire('gesturestart',{target:outsideTarget,expectedPrevented:false});
h.fire('gesturechange',{target:outsideTarget,scale:2,expectedPrevented:false});
h.fire('gestureend',{target:outsideTarget,expectedPrevented:false});close(h.pan.scale,1.4);
console.log('PASS document pinch, native scrolling, cross-surface gestures, unrelated controls');
