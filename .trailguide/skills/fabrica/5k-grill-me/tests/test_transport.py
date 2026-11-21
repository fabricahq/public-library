import copy, importlib.util, json, pathlib, subprocess, sys, tempfile, urllib.request, urllib.error, uuid
root=pathlib.Path(__file__).resolve().parents[1]
script=root/'scripts/grill_ui.py'
spec=importlib.util.spec_from_file_location('grill',script);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
base=json.loads((root/'examples/design.json').read_text()); base['id']='transport-test';base['revision']=1
for mutation in ('cycle','missing','empty-parent'):
    bad=copy.deepcopy(base)
    if mutation=='cycle':bad['nodes'][0]['dependsOn']=[bad['nodes'][0]['id']]
    if mutation=='missing':bad['nodes'][1]['dependsOn']=['MISSING']
    if mutation=='empty-parent':bad['nodes'][1]['parentId']=''
    try:g.validate(bad);raise AssertionError('accepted '+mutation)
    except ValueError:pass
with tempfile.TemporaryDirectory(prefix='grill-test-') as tmp:
    directory=pathlib.Path(tmp);snapshot=directory/'input.json';snapshot.write_text(json.dumps(base))
    def cli(*args):
        return subprocess.run([sys.executable,str(script),*args],capture_output=True,text=True)
    assert cli('publish','--session-dir',tmp,'--snapshot',str(snapshot),'--expected-revision','0').returncode==0
    server=subprocess.Popen([sys.executable,str(script),'serve','--session-dir',tmp],stdout=subprocess.PIPE,text=True)
    try:
        url=json.loads(server.stdout.readline())['url'];origin=url.split('/s/')[0]
        def req(suffix,body=None,foreign=False):
            headers={'Content-Type':'application/json','Origin':'https://example.com' if foreign else origin}
            request=urllib.request.Request(url+suffix,data=json.dumps(body).encode() if body else None,headers=headers)
            try:
                with urllib.request.urlopen(request) as r:return r.status,json.loads(r.read())
            except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
        assert req('state')[1]['listening'] is False
        reply={'id':str(uuid.uuid4()),'kind':'answer','nodeId':'Q5','baseRevision':1,'previousAnswer':None,'text':'Keep the editor small.'}
        assert req('reply',reply,foreign=True)[0]==403
        assert req('reply',reply)[0]==201
        assert req('reply',reply)[0]==200
        assert len(req('state')[1]['pending'])==1
        duplicate=dict(reply,id=str(uuid.uuid4()));assert req('reply',duplicate)[0]==409
        original=reply
        reply=dict(original,id=str(uuid.uuid4()),text='Keep the editor visible.',replaces=original['id'],previousAnswer=original['text'],baseRevision=2)
        assert req('reply',reply)[0]==201, 'Editing a saved answer must replace it'
        assert req('reply',reply)[0]==200, 'Replacement retries are idempotent'
        assert req('reply',original)[0]==200, 'Retrying the old request must not restore it'
        pending=req('state')[1]['pending'];assert len(pending)==1 and pending[0]['text']==reply['text'] and pending[0]['id']==reply['id']
        stale=dict(reply,id=str(uuid.uuid4()),text='Stale tab edit');assert req('reply',stale)[0]==409
        late=copy.deepcopy(base);late['revision']=4;snapshot.write_text(json.dumps(late))
        assert cli('publish','--session-dir',tmp,'--snapshot',str(snapshot),'--expected-revision','3','--ack',original['id']).returncode==1, 'Reject a response based on the replaced answer'
        event=json.loads(cli('wait','--session-dir',tmp,'--timeout','1').stdout)['event'];assert event['id']==reply['id']
        assert req('state')[1]['listening'] is True
        pause={'id':str(uuid.uuid4()),'kind':'pause','baseRevision':1};assert req('reply',pause)[0]==201
        assert json.loads(cli('wait','--session-dir',tmp,'--timeout','1').stdout)['status']=='paused'
        assert cli('ack','--session-dir',tmp,'--event',pause['id']).returncode==0
        updated=copy.deepcopy(req('state')[1]['session']);updated['revision']=4;next(n for n in updated['nodes'] if n['id']=='Q5')['answer']=reply['text']
        updated['nodes'].append({'id':'Q11','parentId':'Q5','title':'A follow-up','question':'Should details remain visible?', 'agentRecommendation':'Keep them available.', 'answer':None,'dependsOn':[]})
        snapshot.write_text(json.dumps(updated))
        assert cli('publish','--session-dir',tmp,'--snapshot',str(snapshot),'--expected-revision','0','--ack',reply['id']).returncode==1
        assert req('state')[1]['session']['revision']==3
        assert cli('publish','--session-dir',tmp,'--snapshot',str(snapshot),'--expected-revision','3','--ack',reply['id']).returncode==0
        state=req('state')[1];assert state['pending']==[] and next(n for n in state['session']['nodes'] if n['id']=='Q5')['answer']==reply['text']
        assert any(n['id']=='Q11' for n in state['session']['nodes']) and any(n['id']!='Q11' and not n.get('answer') for n in state['session']['nodes']), 'Follow-up publishes while other branches remain unanswered'
        assert cli('offline','--session-dir',tmp).returncode==0
        assert req('state')[1]['listening'] is False
        hostile=copy.deepcopy(base);hostile['title']='</script><script>alert(1)</script> __GRILL_BRIDGE__'
        out=g.html(hostile);assert '</script><script>alert(1)' not in out and '__GRILL_BRIDGE__' in out
        print('PASS: malformed trees, durable reply, idempotent retry, duplicate protection, origin rejection, presence, pause priority, atomic acknowledgment, stale revision refusal, script-safe rendering')
    finally:
        server.terminate();server.wait(timeout=5)
