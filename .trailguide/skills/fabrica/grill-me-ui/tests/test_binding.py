import importlib.util,json,pathlib,tempfile,types,subprocess
from unittest.mock import patch
script=pathlib.Path(__file__).resolve().parents[1]/'scripts/grill_ui.py'
spec=importlib.util.spec_from_file_location('grill',script);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d); event={'id':'test-event'}
 cfg={'provider':'codex','sessionId':'00000000-0000-0000-0000-000000000001','transport':'codex-queue','cwd':d,'executable':'/test/codex'}
 g.atomic(p/'connection.json',cfg)
 g.atomic(p/'state.json',{'acknowledged':[],'events':[{'id':ident,'createdAt':0} for ident in ('test-event','unavailable','uncertain')]})
 ok=types.SimpleNamespace(returncode=0)
 with patch.object(g.subprocess,'run',return_value=ok) as run:
  assert g.deliver(p,event)['status']=='sent'
  assert g.deliver(p,event)['status']=='sent'
  assert run.call_count==2
  args=run.call_args_list[1].args[0]
  assert args[:4]==['/test/codex','queue','--thread',cfg['sessionId']]
  assert args[4]=='--message' and 'test-event' in args[5] and str(p) in args[5]
 with patch.object(g.subprocess,'run',return_value=types.SimpleNamespace(returncode=1)) as run:
  assert g.deliver(p,{'id':'unavailable'})['status']=='failed'
  assert run.call_count==1 # no queue and no daemon auto-start
 with patch.object(g.subprocess,'run',side_effect=[ok,subprocess.TimeoutExpired('queue',20)]) as run:
  assert g.deliver(p,{'id':'uncertain'})['status']=='unknown'
  assert g.deliver(p,{'id':'uncertain'})['status']=='unknown'
  assert run.call_count==2
 state=g.read(p/'state.json');state['events'].append({'id':'replacement','replaces':'test-event','createdAt':1});g.atomic(p/'state.json',state)
 with patch.object(g.subprocess,'run') as run:
  assert g.deliver(p,event)['status']=='superseded'
  run.assert_not_called()
 args=types.SimpleNamespace(agent_session=cfg['sessionId'],provider='codex',transport='codex-queue',cwd=p,session_dir=p)
 with patch.object(g.shutil,'which',return_value='/test/codex'),patch.object(g.subprocess,'run',return_value=types.SimpleNamespace(returncode=1)):
  try:g.bind(args);raise AssertionError('bound without daemon')
  except ValueError:pass
  assert g.connection(p)==cfg
 args.transport='auto'
 with patch.object(g.shutil,'which',return_value='/test/codex'),patch.object(g.subprocess,'run',return_value=ok),patch.object(g,'verify_codex_thread') as verify:
  assert g.bind(args)['connection']['transport']=='codex-queue'
  verify.assert_called_once_with('/test/codex',cfg['sessionId'])
 with patch.object(g.shutil,'which',return_value='/test/codex'),patch.object(g.subprocess,'run',return_value=ok),patch.object(g,'verify_codex_thread',side_effect=ValueError('Different host')):
  assert g.bind(args)['connection']['transport']=='inbox'
 # A queued receipt cannot be redirected by a later binding change.
 g.atomic(p/'connection.json',dict(cfg,sessionId='00000000-0000-0000-0000-000000000002'))
 state=g.read(p/'state.json');state['events'].append({'id':'route-change','createdAt':2});g.atomic(p/'state.json',state)
 g.atomic(p/'deliveries/route-change.json',{'status':'queued','route':{k:cfg[k] for k in ('provider','transport','sessionId')}})
 with patch.object(g.subprocess,'run') as run:
  assert g.deliver(p,{'id':'route-change'})['status']=='failed';run.assert_not_called()
 forest=json.loads((pathlib.Path(__file__).resolve().parents[1]/'examples/design.json').read_text());assert len([n for n in g.validate(forest)['nodes'] if n['parentId'] is None])==3
 forest['nodes'][0]['parentId']='missing'
 try:g.validate(forest);raise AssertionError('accepted invalid parent')
 except ValueError:pass
 print('PASS forest validation, exact session routing, delivery receipts, no duplicate send, unavailable daemon, uncertain timeout, bind failure preserves configuration')
