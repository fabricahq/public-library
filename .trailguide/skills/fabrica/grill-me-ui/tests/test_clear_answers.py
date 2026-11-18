"""Exercise saved decisions and review history through the real local HTTP API."""
import copy, importlib.util, json, pathlib, subprocess, sys, tempfile, types, urllib.request, urllib.error, uuid
root = pathlib.Path(__file__).resolve().parents[1]
script = root / 'scripts/grill_ui.py'
spec = importlib.util.spec_from_file_location('grill', script)
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
def node(ident, parent=None, answer='Yes', depends=()):
    return dict(id=ident, title=ident, question=f'Question {ident}?', parentId=parent, answer=answer, dependsOn=list(depends))
base = dict(id='review-test', title='Answer review test', revision=1, nodes=[node('Q1'), node('Q2','Q1'), node('Q3',depends=['Q2']), node('Q4'), node('Q5','Q3',None)])
with tempfile.TemporaryDirectory(prefix='grill-review-') as tmp:
    directory=pathlib.Path(tmp);snapshot=directory/'input.json';snapshot.write_text(json.dumps(base))
    g.publish(types.SimpleNamespace(session_dir=directory,snapshot=snapshot,expected_revision=0,ack=None))
    def start():
        server=subprocess.Popen([sys.executable,str(script),'serve','--session-dir',tmp],stdout=subprocess.PIPE,text=True)
        return server,json.loads(server.stdout.readline())['url']
    server,url=start()
    try:
        def req(suffix,body=None,foreign=False):
            request=urllib.request.Request(url+suffix,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json','Origin':'https://example.com' if foreign else url.split('/s/')[0]})
            try:
                with urllib.request.urlopen(request) as response:return response.status,json.loads(response.read())
            except urllib.error.HTTPError as error:return error.code,json.loads(error.read())
        def current():return req('state')[1]
        def nodes():return {n['id']:n for n in current()['session']['nodes']}
        def payload(ident,text,confirmation=False):
            state=current();n=next(n for n in state['session']['nodes'] if n['id']==ident)
            saved=next((e for e in state['pending'] if e['kind']=='answer' and e['nodeId']==ident),None)
            return dict(id=str(uuid.uuid4()),kind='answer',nodeId=ident,baseRevision=state['session']['revision'],previousAnswer=n['answer'],text=text,replaces=saved['id'] if saved else None,confirmation=confirmation)
        stale=payload('Q2','Stale child edit')
        first=payload('Q1','Local only')
        assert req('reply',first,True)[0]==403
        assert req('reply',first)[0]==201
        state=current();rev=state['session']['revision']
        assert nodes()['Q1']['answer']=='Local only', 'Submission updates the design before agent acknowledgment'
        assert g.read(directory/'state.json')['session']['nodes'][0]['answer']=='Local only'
        assert first['id'] not in state['acknowledged']
        assert not g.current_answer(state,'Q2') and not g.current_answer(state,'Q3')
        assert g.current_answer(state,'Q4')
        assert req('reply',first)[0]==200 and current()['session']['revision']==rev
        assert req('reply',stale)[0]==409, 'Stale edits cannot confirm against changed prerequisites'
        same=payload('Q1','Local only',True);assert req('reply',same)[0]==201
        assert current()['answerState']['Q1']['changedAt']==rev
        assert not g.current_answer(current(),'Q2'), 'Same-text confirmation does not approve descendants'
        assert req('reply',payload('Q3','Yes',True))[0]==409, 'Review prerequisites before keeping a dependent answer'
        keep=payload('Q2','Yes',True);assert req('reply',keep)[0]==201
        assert g.current_answer(current(),'Q2') and not g.current_answer(current(),'Q3')
        assert req('reply',payload('Q3','Yes',True))[0]==201
        assert g.current_answer(current(),'Q3')
        assert req('reply',payload('Q5','Tentative'))[0]==201
        replacement=payload('Q1','Sync across devices');assert req('reply',replacement)[0]==201
        assert nodes()['Q1']['answer']=='Sync across devices' and not g.current_answer(current(),'Q5')
        assert req('reply',first)[0]==200 and nodes()['Q1']['answer']=='Sync across devices', 'Retry never restores an old answer'
        prior=current()
        server.terminate();server.wait(timeout=5);server,url=start()
        assert current()['answerState']==prior['answerState'] and not g.current_answer(current(),'Q2')
        before=current();bad=copy.deepcopy(before['session']);bad['revision']+=1;bad['nodes'][0]['answer']='Overwrite pending answer';snapshot.write_text(json.dumps(bad))
        try:g.publish(types.SimpleNamespace(session_dir=directory,snapshot=snapshot,expected_revision=before['session']['revision'],ack=None));raise AssertionError('Overwrote pending answer')
        except ValueError:pass
        # Delivery acknowledgment is not user confirmation.
        good=copy.deepcopy(before['session']);good['revision']+=1;snapshot.write_text(json.dumps(good))
        g.publish(types.SimpleNamespace(session_dir=directory,snapshot=snapshot,expected_revision=before['session']['revision'],ack=replacement['id']))
        assert not g.current_answer(current(),'Q2')
        clear=dict(id=str(uuid.uuid4()),nodeId='Q1',baseRevision=current()['session']['revision'])
        assert req('clear',clear)[0]==201
        assert nodes()['Q1']['answer'] is None and nodes()['Q2']['answer']=='Yes'
        cleared_rev=current()['session']['revision']
        assert req('clear',clear)[0]==200 and current()['session']['revision']==cleared_rev
        assert req('clear',{**clear,'id':str(uuid.uuid4()),'nodeId':'Q4'})[0]==409
        assert req('reply',payload('Q1','Local only'))[0]==201
        assert not g.current_answer(current(),'Q2'), 'Restoring an old value still requires review'
        # Optional source changes are harmless; a changed question requires reconfirmation.
        state=current();s=copy.deepcopy(state['session']);s['revision']+=1;s['nodes'][3]['notes']='More context';snapshot.write_text(json.dumps(s))
        g.publish(types.SimpleNamespace(session_dir=directory,snapshot=snapshot,expected_revision=state['session']['revision'],ack=None));assert g.current_answer(current(),'Q4')
        state=current();s=copy.deepcopy(state['session']);s['revision']+=1;s['nodes'][3]['question']='A changed question?';snapshot.write_text(json.dumps(s))
        g.publish(types.SimpleNamespace(session_dir=directory,snapshot=snapshot,expected_revision=state['session']['revision'],ack=None));assert not g.current_answer(current(),'Q4')
        # An exported session restores review history, draft text, and pending delivery independently.
        state=current();export={k:state[k] for k in ('session','answerState','pending')};export.update(drafts={'Q2':'Unfinished'},draftContexts={'Q2':{'baseRevision':state['session']['revision'],'previousAnswer':'Yes'}})
        snapshot.write_text(json.dumps(export));restored=directory/'restored'
        g.publish(types.SimpleNamespace(session_dir=restored,snapshot=snapshot,expected_revision=0,ack=None))
        recovered=g.read(restored/'state.json')
        assert recovered['answerState']==state['answerState'] and recovered['session']==state['session']
        assert recovered['drafts']['Q2']=='Unfinished' and len(g.pending(recovered))==len(state['pending'])
        assert not g.current_answer(recovered,'Q2')
        rendered=subprocess.run([sys.executable,str(script),'render','--snapshot',str(snapshot),'--output',str(directory/'restored.html')],capture_output=True,text=True)
        assert rendered.returncode==0,rendered.stderr
        embedded,_=json.JSONDecoder().raw_decode((directory/'restored.html').read_text().split('<script type="application/json" id="initialAppState">',1)[1])
        assert embedded['answerState']==state['answerState'] and embedded['drafts']['Q2']=='Unfinished'
        assert all('needsReview' not in n for n in state['session']['nodes'])
        print('PASS immediate answers, durable review, confirmations, stale edits, retries, atomic receipts, clear, publish, restart and export restoration')
    finally:
        server.terminate();server.wait(timeout=5)
