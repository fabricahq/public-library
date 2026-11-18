"""Real loopback regression: a slow agent queue must not delay saving an answer."""
import copy, json, os, pathlib, subprocess, sys, tempfile, time, urllib.request, uuid
root=pathlib.Path(__file__).resolve().parents[1]; script=root/'scripts/grill_ui.py'
with tempfile.TemporaryDirectory(prefix='grill-live-') as tmp:
 p=pathlib.Path(tmp)
 def cli(*args):
  r=subprocess.run([sys.executable,str(script),*args],capture_output=True,text=True);assert r.returncode==0,r.stderr;return json.loads(r.stdout)
 cli('publish','--session-dir',tmp,'--snapshot',str(root/'examples/design-context.json'),'--expected-revision','0')
 fake=p/'codex';fake.write_text('#!/usr/bin/env python3\nimport sys,time,pathlib\nif sys.argv[1]=="queue":\n with pathlib.Path("queue-count").open("a") as f: f.write("sent\\n")\n time.sleep(2)\n');fake.chmod(0o700)
 (p/'connection.json').write_text(json.dumps({'provider':'codex','transport':'codex-queue','sessionId':str(uuid.uuid4()),'cwd':tmp,'executable':str(fake)}))
 server=subprocess.Popen([sys.executable,str(script),'serve','--session-dir',tmp],stdout=subprocess.PIPE,text=True)
 try:
  url=json.loads(server.stdout.readline())['url'];origin=url.split('/s/')[0]
  def req(route,body=None):
   request=urllib.request.Request(url+route,data=json.dumps(body).encode() if body else None,headers={'Origin':origin,'Content-Type':'application/json'})
   with urllib.request.urlopen(request,timeout=5) as r:return json.loads(r.read())
  event={'id':str(uuid.uuid4()),'nodeId':'Q2','kind':'answer','baseRevision':1,'previousAnswer':None,'text':'Keep it contextual.'}
  before=time.monotonic();req('reply',event);elapsed=time.monotonic()-before
  assert elapsed<0.75, f'Save waited for agent delivery: {elapsed:.2f}s'
  # Retrying the same HTTP request must not enqueue a second prompt.
  req('reply',event)
  deadline=time.monotonic()+5
  while time.monotonic()<deadline:
   pending=req('state')['pending']
   if pending[0]['delivery']['status']=='sent': break
   time.sleep(.05)
  assert pending[0]['delivery']['status']=='sent'
  assert (p/'queue-count').read_text().splitlines()==['sent']
  received=cli('receive','--session-dir',tmp,'--event',event['id'])['event']['receivedAt']
  assert cli('receive','--session-dir',tmp,'--event',event['id'])['event']['receivedAt']==received
  snapshot=req('state')['session'];snapshot['revision']+=1
  f=p/'next.json';f.write_text(json.dumps(snapshot))
  cli('publish','--session-dir',tmp,'--snapshot',str(f),'--expected-revision','2','--ack',event['id'])
  timing=cli('timings','--session-dir',tmp)['events'][0]
  assert timing['times']['createdAt'] <= timing['times']['receivedAt'] <= timing['times']['publishedAt']
  assert timing['secondsFromSave']['sentAt'] >= 2
  print('PASS durable receipt timestamps and idempotent receive/publish')
  print('PASS immediate durable save despite slow queue:',round(elapsed,3),'seconds')
 finally:server.terminate();server.wait(timeout=5)
