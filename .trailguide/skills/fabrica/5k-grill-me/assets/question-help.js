// Help is supporting content. Its local view and requests never edit an answer.
const questionHelpViews = new Map(), questionHelpRequests = new Map();
function questionHelpView(n) {
  const key = JSON.stringify([n.question, recommendationText(n)]);
  if (questionHelpViews.get(n.id)?.key !== key) questionHelpViews.set(n.id, {key, mode:null, level:'eli15', step:0});
  return questionHelpViews.get(n.id);
}
function currentQuestionHelp(n) {
  const help = n.help;
  if (!help || help.sourceQuestion !== n.question || help.sourceRecommendation !== recommendationText(n) || help.basedOnRevision > session.revision) return null;
  const seen = new Set(), queue = [n.id];
  while (queue.length) {
    const id = queue.pop();
    if (seen.has(id)) continue;
    seen.add(id);
    if ((answerState[id]?.changedAt ?? session.revision) > help.basedOnRevision) return null;
    queue.push(...deps(get(id)));
  }
  return help;
}
function pendingQuestionHelp(n) {
  return inbox.find(event => event.kind === 'help' && event.nodeId === n.id && event.question === n.question);
}
function questionHelpProgress() {
  const pendingHelp = inbox.filter(event => event.kind === 'help');
  if (!pendingHelp.length || !connected || (!listening && !directDelivery())) return null;
  if (pendingHelp.some(event => ['failed','unknown'].includes(event.delivery?.status))) return null;
  const working = pendingHelp.some(event => event.receivedAt);
  return {activity:working ? 'reviewing' : 'waiting', title:working ? 'Agent is preparing question help' : 'Waiting for the agent to receive your help request',
    description:'Your answers are unchanged. The explanation will appear here when it is ready.'};
}
function questionHelpPrompt(n) {
  return `Use the 5k-grill-me skill to help me understand ${n.id}: ${n.title}. Read references/question-help.md. Prepare ELI-15 (really simple), ELI-18, and a concrete scenario walkthrough in this node's help field for the current revision. Preserve every question, recommendation, answer, and draft. This is not an answer or permission to implement.\n\nSession: ${session.id}\n${bridge?.sessionDir ? 'Canvas files: ' + bridge.sessionDir + '\n' : ''}Question: ${n.question}\nRecommendation: ${recommendationText(n) || '(None)'}\n${pendingQuestionHelp(n) ? 'Acknowledge help receipt: ' + pendingQuestionHelp(n).id + '\n' : ''}\nCurrent design:\n${sessionExport()}`;
}
function questionHelpContent() {
  return '<div id="questionHelp" class="question-help"></div>';
}
function helpParagraphs(paragraphs) {
  return paragraphs.map(text => `<p>${esc(text)}</p>`).join('');
}
function helpVisual(visual) {
  if (!visual) return '';
  return `<figure class="help-visual"><figcaption>${esc(visual.title)}</figcaption><ul>${visual.items.map(item => `<li class="help-visual-${item.state || 'neutral'}"><span class="help-visual-symbol" aria-hidden="true">${item.state === 'included' ? '✓' : item.state === 'excluded' ? '×' : '•'}</span><div><strong>${esc(item.label)}</strong>${item.detail ? `<span>${esc(item.detail)}</span>` : ''}</div>${item.state && item.state !== 'neutral' ? `<small>${item.state === 'included' ? 'Included' : 'Excluded'}</small>` : ''}</li>`).join('')}</ul>${visual.caption ? `<p>${esc(visual.caption)}</p>` : ''}</figure>`;
}
function renderQuestionHelp(n, windowRoot = null, windowMode = null) {
  const root = windowRoot || document.getElementById('questionHelp');
  if (!root || (!windowRoot && selected !== n.id)) return;
  const $ = id => windowRoot ? root.querySelector(`[data-help-control="${id}"]`) : document.getElementById(id);
  n = get(n.id);
  if (!n) return;
  const focused = root.contains(document.activeElement) ? (windowRoot ? document.activeElement.dataset.helpControl : document.activeElement.id) : null;
  const view = questionHelpView(n), help = currentQuestionHelp(n), pendingHelp = pendingQuestionHelp(n), request = questionHelpRequests.get(n.id);
  const opening = windowMode || (innerWidth < 1000 ? view.mode : null);
  const repaint = () => renderQuestionHelp(n, windowRoot, windowMode);
  const close = () => {
    if (windowRoot) closeQuestionHelpWindow(n.id, windowMode);
    else { view.mode=null; repaint(); $(opening === 'simple' ? 'helpSimple' : 'helpWalk')?.focus({preventScroll:true}); }
  };
  let body = '';
  if (opening && !help) {
    const received = pendingHelp?.receivedAt, delivery = pendingHelp?.delivery?.status;
    const canDeliver = bridge && connected && (listening || directDelivery());
    const failed = ['failed','unknown'].includes(delivery) || (request?.error && !pendingHelp);
    const title = request?.busy ? 'Requesting help…' : failed ? 'Help has not arrived yet' : received && canDeliver ? 'The agent is preparing your explanation' : pendingHelp && canDeliver ? 'Waiting for the agent' : n.help ? 'This explanation needs an update' : 'Ask your agent to explain this question';
    const description = failed ? 'You can copy the request into your agent chat. Your answer is unchanged.' : pendingHelp && canDeliver ? 'This panel will update when the agent publishes the explanation. Your answer is unchanged.' : 'Copy the request into your agent chat. The agent can prepare a simpler explanation and a walkthrough for this question.';
    body = `<div class="help-empty" role="status"><h4>${esc(title)}</h4><p>${description}</p>${request?.error ? `<p class="help-error">${esc(request.error)}</p>` : ''}<div class="help-recovery"><button class="text-btn copy-action" id="copyHelpRequest">${copyIcon()}<span>Copy request for agent</span></button>${!request?.busy && !pendingHelp && bridge && connected ? '<button class="secondary" id="retryHelpRequest">Request help</button>' : ''}</div></div>`;
  } else if (opening === 'simple') {
    const explanation = help[view.level];
    body = `<div class="help-level" role="group" aria-label="Explanation level"><button id="helpEli15" aria-pressed="${view.level === 'eli15'}">ELI-15 (really simple)</button><button id="helpEli18" title="More detail, with technical terms explained" aria-pressed="${view.level === 'eli18'}">ELI-18</button></div><div class="help-explanation" aria-live="polite"><h4>${esc(explanation.title)}</h4>${helpParagraphs(explanation.paragraphs)}<div class="help-decision"><strong>What you’re deciding</strong><p>${esc(explanation.decision)}</p></div>${explanation.limits ? `<details class="help-limits"><summary>Limits that still apply</summary><p>${esc(explanation.limits)}</p></details>` : ''}</div><div class="help-footer"><button class="text-btn" id="helpShowExample">Show me an example →</button><button class="secondary" id="helpGotIt">Got it</button></div>`;
  } else if (opening === 'walk') {
    view.step = Math.min(view.step, help.walkthrough.steps.length - 1);
    const steps = help.walkthrough.steps, step = steps[view.step];
    body = `<div class="help-step-heading"><span role="status">Step ${view.step + 1} of ${steps.length}</span><span>${esc(help.walkthrough.title)}</span></div><div class="help-step-progress" aria-hidden="true">${steps.map((_, i) => `<span class="${i <= view.step ? 'visited' : ''}"></span>`).join('')}</div><div class="help-scene" aria-live="polite"><div><h4>${esc(step.title)}</h4>${helpParagraphs(step.paragraphs)}</div>${helpVisual(step.visual)}</div><div class="help-navigation"><button class="secondary" id="helpPrevious" ${view.step === 0 ? 'disabled' : ''}>Previous step</button><button class="secondary" id="helpNext">${view.step === steps.length - 1 ? 'Continue to answer' : 'Next →'}</button></div><div class="help-footer"><button class="text-btn" id="helpShortVersion">Give me the short version</button></div>`;
  }
  const markup = `<div class="question-help-actions"><button id="helpSimple" class="secondary" aria-expanded="${opening === 'simple'}" aria-controls="questionHelpBody"><span aria-hidden="true">?</span> Wait, what?</button><button id="helpWalk" class="secondary" aria-expanded="${opening === 'walk'}" aria-controls="questionHelpBody"><span aria-hidden="true">▷</span> Walk me through it</button></div>${opening ? `<section id="questionHelpBody" class="question-help-body" aria-labelledby="questionHelpTitle"><div class="question-help-heading"><h3 id="questionHelpTitle" tabindex="-1">${opening === 'simple' ? 'The same question, more simply' : 'Walk through a scenario'}</h3><button id="helpClose" aria-label="Close question help">×</button></div><div class="question-help-content">${body}</div><p class="help-disclaimer">Explanation only. Your answer has not changed.</p></section>` : ''}`;
  const template = document.createElement('template');
  template.innerHTML = markup;
  if (windowRoot) {
    template.content.querySelector('.question-help-actions').remove();
    template.content.querySelector('#helpClose').remove();
    for (const element of template.content.querySelectorAll('[id]')) {
      const id = element.id; element.dataset.helpControl = id; element.id = windowRoot.id + '-' + id;
    }
    template.content.querySelector('section').setAttribute('aria-labelledby', windowRoot.id + '-questionHelpTitle');
    const context = document.createElement('div'); context.className='help-window-context';
    context.innerHTML = `<strong>${esc(n.id)} · ${esc(n.title)}</strong><details><summary>Original question</summary><p>${esc(n.question)}</p></details>`;
    template.content.prepend(context);
  }
  root.replaceChildren(template.content);
  if (!windowRoot && innerWidth >= 1000) {
    for (const id of ['helpSimple','helpWalk']) {
      $(id).removeAttribute('aria-expanded'); $(id).removeAttribute('aria-controls');
      $(id).title = 'Open in a canvas window';
    }
  }
  const toggle = mode => {
    if (innerWidth >= 1000) { openQuestionHelpWindow(n, mode); return; }
    const closing = view.mode === mode; view.mode = closing ? null : mode;
    repaint();
    if (closing) $(mode === 'simple' ? 'helpSimple' : 'helpWalk').focus({preventScroll:true});
    else {
      $('questionHelpTitle').focus({preventScroll:true});
      if (innerWidth <= 650) $('questionHelpBody').scrollIntoView({block:'start',behavior:'instant'});
      if (!currentQuestionHelp(n) && !pendingQuestionHelp(n) && !questionHelpRequests.get(n.id)?.busy && bridge && connected) requestQuestionHelp(n);
    }
  };
  if (!windowRoot) { $('helpSimple').onclick = () => toggle('simple'); $('helpWalk').onclick = () => toggle('walk'); }
  if (opening) {
    if ($('helpClose')) $('helpClose').onclick = close;
    root.onkeydown = event => { if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); if (windowRoot && maximizedArtifactId === questionHelpWindowId(n.id, windowMode)) restoreMaximizedArtifact(); else close(); } };
  } else root.onkeydown = null;
  if ($('copyHelpRequest')) $('copyHelpRequest').onclick = () => copyReply(questionHelpPrompt(n), $('copyHelpRequest'), {subject:'help request'});
  if ($('retryHelpRequest')) $('retryHelpRequest').onclick = () => requestQuestionHelp(n);
  if ($('helpEli15')) {
    for (const [id,level] of [['helpEli15','eli15'],['helpEli18','eli18']]) $(id).onclick = () => { view.level=level; repaint(); $(id).focus({preventScroll:true}); };
    $('helpShowExample').onclick = () => toggle('walk');
    $('helpGotIt').onclick = close;
  }
  if ($('helpNext')) {
    $('helpPrevious').onclick = () => {view.step--; repaint(); $('helpNext').focus({preventScroll:true});};
    $('helpNext').onclick = () => {
      if (view.step === help.walkthrough.steps.length - 1) {
        close();
        if (selected !== n.id) select(n.id);
        const target = document.getElementById('draft') || document.getElementById('recommendationTab') || document.getElementById('editAnswer') || document.getElementById('helpWalk');
        target.focus({preventScroll:true}); target.scrollIntoView({block:'nearest',behavior:'instant'});
      } else { view.step++; repaint(); $('helpNext').focus({preventScroll:true}); }
    };
    $('helpShortVersion').onclick = () => toggle('simple');
  }
  if (focused && $(focused)) $(focused).focus({preventScroll:true});
}
async function requestQuestionHelp(n) {
  const key = JSON.stringify([n.question, session.revision]);
  let request = questionHelpRequests.get(n.id);
  if (request?.busy) return;
  if (!request || request.key !== key) request = {key, id:crypto.randomUUID()};
  request.busy=true; request.error=null; questionHelpRequests.set(n.id,request); renderQuestionHelp(n); renderArtifacts();
  const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(bridge.base + 'reply', {method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,
      body:JSON.stringify({id:request.id,kind:'help',nodeId:n.id,question:n.question,baseRevision:session.revision})});
    if (!response.ok) throw Error((await response.json()).error || 'Could not request help.');
    await refresh();
  } catch (error) {
    request.error = error.name === 'AbortError' ? 'Delivery is unconfirmed. Check your agent chat or copy the request.' : error.message;
  } finally {
    clearTimeout(timeout); request.busy=false;
    renderQuestionHelp(n); renderArtifacts();
  }
}

function questionHelpWindowId(nodeId, mode) { return 'question-help:' + nodeId + ':' + mode; }
function questionHelpWindowFiles() {
  if (innerWidth < 1000) return [];
  return session.nodes.flatMap(n => ['simple','walk'].map(mode => ({
    id:questionHelpWindowId(n.id, mode), kind:'help', nodeId:n.id, mode, derived:true,
    title:n.id + ' · ' + (mode === 'simple' ? 'Wait, what?' : 'Walk me through it')
  })));
}
function openQuestionHelpWindow(n, mode) {
  const id = questionHelpWindowId(n.id, mode);
  if (maximizedArtifactId && maximizedArtifactId !== id) restoreMaximizedArtifact();
  questionHelpView(n).mode = mode;
  let view = artifactViews[id];
  if (!view || !artifactVisible(view)) {
    const {w,h} = available(), width = Math.min(mode === 'walk' ? 620 : 510, w - 32), height = Math.min(mode === 'simple' ? 760 : 660, h - 48);
    const offset = mode === 'walk' ? 36 : 0;
    view = artifactViews[id] = {...newArtifactView(), x:(16 + Math.min(offset, Math.max(0,w-width-32)) - pan.x)/pan.scale,
      y:(20 + Math.min(offset,Math.max(0,h-height-40)) - pan.y)/pan.scale, width:width/pan.scale, height:height/pan.scale, zoom:documentZoom(Math.round(4/pan.scale)/4)};
  }
  view.minimized = false;
  renderArtifacts();
  const element = artifactWindows.get(id);
  element.style.zIndex = ++artifactOrder;
  element.querySelector('.artifact-drag').focus({preventScroll:true});
  saveArtifactViews();
  if (!currentQuestionHelp(n) && !pendingQuestionHelp(n) && !questionHelpRequests.get(n.id)?.busy && bridge && connected) requestQuestionHelp(n);
}
function closeQuestionHelpWindow(nodeId, mode) {
  const id = questionHelpWindowId(nodeId, mode);
  if (maximizedArtifactId === id) restoreMaximizedArtifact();
  delete artifactViews[id];
  if (questionHelpViews.get(nodeId)?.mode === mode) questionHelpViews.get(nodeId).mode=null;
  renderArtifacts(); saveArtifactViews();
  if (selected === nodeId) document.getElementById(mode === 'simple' ? 'helpSimple' : 'helpWalk')?.focus({preventScroll:true});
  else document.getElementById('presence').focus({preventScroll:true});
}
function renderQuestionHelpWindow(file, element) {
  const n = get(file.nodeId), view = questionHelpView(n);
  element.classList.add('help-window');
  element.onkeydown = event => {
    if (event.key !== 'Escape') return;
    event.preventDefault(); event.stopPropagation();
    if (maximizedArtifactId === file.id) restoreMaximizedArtifact();
    else closeQuestionHelpWindow(file.nodeId, file.mode);
  };
  const maximize = element.querySelector('.artifact-maximize');
  maximize.setAttribute('aria-label', maximizedArtifactId === file.id ? 'Restore window size' : 'Maximize help window');
  maximize.title = maximizedArtifactId === file.id ? 'Restore window size (Esc)' : 'Maximize help window';
  element.querySelector('.artifact-close').title = 'Close help window';
  element.querySelector('.artifact-minimize').title = artifactViews[file.id].minimized ? 'Restore help window' : 'Minimize to title bar';
  element.querySelector('.artifact-body').setAttribute('aria-label', 'Question help');
  element.querySelector('.document-zoom').setAttribute('aria-label', 'Help zoom');
  element.querySelector('.artifact-close').setAttribute('aria-label', 'Close ' + file.title);
  element.querySelector('.contents-toggle').hidden = true;
  element.querySelector('.artifact-toc').hidden = true;
  element.querySelector('.artifact-body').onscroll = () => updateHelpScroll(element);
  element.querySelector('.artifact-status').title = '';
  element.querySelector('.artifact-body').dataset.mode = 'rendered';
  const body = element.querySelector('.artifact-document');
  body.id = file.id + '-content';
  const signature = JSON.stringify([n, currentQuestionHelp(n), pendingQuestionHelp(n), questionHelpRequests.get(n.id), view.level, view.step, connected, listening]);
  if (element.helpSignature !== signature) {
    element.helpSignature = signature;
    renderQuestionHelp(n, body, file.mode);
  }
  updateHelpScroll(element);
}
function updateHelpScroll(element) {
  const body = element.querySelector('.artifact-body');
  const more = body.scrollHeight - body.clientHeight - body.scrollTop > 8;
  element.querySelector('.artifact-status').textContent = more ? 'Scroll for more ↓' : 'Question help';
}
