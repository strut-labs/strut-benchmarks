import subprocess,os,time,http.client,json,socket
results={}
for tag in ('base','cand'):
 env=dict(os.environ,STRUT_HTTP_REACTOR='1',STRUT_WORKERS='1')
 trace='/tmp/r85-'+tag+'.trace'
 p=subprocess.Popen(['strace','-f','-e','trace=epoll_ctl,writev','-o',trace,'/tmp/r85-'+tag+'-server'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 try:
  for i in range(100):
   try:
    c=http.client.HTTPConnection('127.0.0.1',8080,timeout=3);c.connect();break
   except OSError:time.sleep(.05)
  for i in range(100):
   c.request('GET','/plaintext');r=c.getresponse();assert r.status==200 and r.read()==b'Hello, World!'
  c.request('GET','/json');r=c.getresponse();assert r.status==200 and json.loads(r.read())=={'message':'Hello, World!'}
  c.request('GET','/missing');r=c.getresponse();assert r.status==404;r.read();c.close()
 finally:
  # Stop the exact traced server child, then its tracer.
  children=open('/proc/%s/task/%s/children'%(p.pid,p.pid)).read().split() if p.poll() is None else []
  for child in children:os.kill(int(child),15)
  try:p.communicate(timeout=5)
  except subprocess.TimeoutExpired:p.terminate();p.communicate()
 text=open(trace).read();results[tag]={'epoll_ctl':text.count('epoll_ctl('),'writev':text.count('writev('),'functional':'100 keep-alive plaintext, JSON, 404 passed'}
print(json.dumps(results,indent=2))
open('/tmp/r85-local-results.json','w').write(json.dumps(results,indent=2))
