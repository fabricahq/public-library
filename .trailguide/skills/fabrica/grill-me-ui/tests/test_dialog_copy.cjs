const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/canvas.html'), 'utf8');
const handler = source.slice(source.indexOf('      $("copy").onclick = async'), source.indexOf('      document.addEventListener("keydown"'));
const fullMessage = 'Questions and answers\n' + 'Unfinished draft\n'.repeat(1000);
let selected = false, copied, confirmed;
const elements = {
  copy: {}, copyLabel: {textContent:"Copy this message"}, copyFeedback: {},
  copyText: {value:fullMessage, focus() {}, select() {selected = true;}},
};
const context = {showCopySuccess:button=>{confirmed=button;}, $:id => elements[id], navigator:{clipboard:{writeText:async text => {copied = text;}}}, setTimeout, clearTimeout};
vm.runInNewContext(handler, context);
(async () => {
  await elements.copy.onclick();
  assert.equal(copied, fullMessage, 'copies the entire message, including content below the visible area');
  assert.equal(selected, false, 'successful copy must not require manual selection');
  assert.equal(elements.copyLabel.textContent, 'Copy this message');
  assert.equal(confirmed, elements.copy);
  assert.equal(elements.copyFeedback.textContent, "");
  assert.equal(elements.copy.disabled, false);
  context.navigator.clipboard.writeText = async () => {throw Error('denied');};
  await elements.copy.onclick();
  assert.equal(selected, true);
  assert.match(elements.copyFeedback.textContent, /browser blocked copying/);
  selected = false;
  context.navigator.clipboard.writeText = () => new Promise(() => {});
  await elements.copy.onclick();
  assert.equal(selected, true, 'pending permission must offer recovery');
  assert.equal(elements.copy.disabled, false);
  console.log('PASS full message copy, no manual selection on success, denied and pending clipboard recovery');
})().catch(error => {console.error(error);process.exitCode = 1;});
