"""Recovery preserves delivery intent without duplicates or implicit chat activation."""
import importlib.util, json, pathlib, tempfile, time, types, uuid
from unittest.mock import patch
script=pathlib.Path(__file__).resolve().parents[1]/'scripts/grill_ui.py'
spec=importlib.util.spec_from_file_location('grill',script);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);ident=str(uuid.uuid4())
 config={'provider':'codex','sessionId':ident,'transport':'codex-queue','cwd':tmp,'executable':'/fake/codex'}
 route={k:config[k] for k in ('provider','sessionId','transport')}
 events=[{'id':str(uuid.uuid4()),'createdAt':time.time(),'kind':'answer','deliveryRequested':route} for _ in range(4)]
 events[3]['replaces']=events[2]['id']
 g.atomic(p/'state.json',{'events':events,'acknowledged':[]});g.atomic(p/'connection.json',config)
 interrupted=p/'deliveries'/(events[1]['id']+'.json');g.atomic(interrupted,{'status':'sending'})
 with patch.object(g.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)) as run:
  worker=g.DeliveryWorker(p)
  try:
   deadline=time.monotonic()+3
   while time.monotonic()<deadline:
    last=p/'deliveries'/(events[3]['id']+'.json')
    if last.exists() and g.read(last)['status']=='sent':break
    time.sleep(.02)
   assert g.read(last)['status']=='sent'
   assert g.read(p/'deliveries'/(events[0]['id']+'.json'))['status']=='sent'
   assert g.read(interrupted)['status']=='unknown'
   assert not (p/'deliveries'/(events[2]['id']+'.json')).exists()
   assert run.call_count==4, 'Only two current, unsent receipts can send'
   try:g.receive(p,events[2]['id']);raise AssertionError('received replaced event')
   except ValueError:pass
  finally:worker.close()
 # Exercise real JSON-RPC framing, including split lines, without starting a host.
 fake=p/'proxy';fake.write_text('''#!/usr/bin/env python3
import json,sys,time
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r: continue
 result={} if r['method']=='initialize' else {'thread':{'id':r['params']['threadId'],'status':{'type':sys.argv[-1]}}}
 output=json.dumps({'id':r['id'],'result':result})+'\\n'
 sys.stdout.write(output[:5]);sys.stdout.flush();time.sleep(.01)
 sys.stdout.write(output[5:]);sys.stdout.flush()
''');fake.chmod(0o700)
 original=g.subprocess.Popen
 for status in ('idle','active','notLoaded','systemError'):
  def launch(argv,**kw):return original([str(fake),status],**kw)
  with patch.object(g.subprocess,'Popen',side_effect=launch):
   if status in ('idle','active'):g.verify_codex_thread(str(fake),ident)
   else:
    try:g.verify_codex_thread(str(fake),ident);raise AssertionError('accepted unloaded chat')
    except ValueError:pass
 print('PASS restart recovery, uncertain-send retention, supersession, exact loaded-chat verification and fragmented host responses')
