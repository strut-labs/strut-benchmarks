import os,subprocess,socket,time,http.client,json
p=subprocess.Popen(['/tmp/r85-backpressure-server'],env=dict(os.environ,STRUT_HTTP_REACTOR='1',STRUT_WORKERS='1'))
try:
 for i in range(100):
  try:s=socket.create_connection(('127.0.0.1',18080),timeout=10);break
  except OSError:time.sleep(.05)
 s.sendall(b'GET /plaintext HTTP/1.1\r\nHost: local\r\n\r\n');time.sleep(.3)
 r=http.client.HTTPResponse(s);r.begin();body=r.read();assert len(body)==8*1024*1024 and body==b'x'*len(body);s.close()
 # Pipelined responses force finish->pump->worker dispatch before the next drain.
 s=socket.create_connection(('127.0.0.1',18080),timeout=10);s.sendall(b'GET /json HTTP/1.1\r\nHost: local\r\n\r\n'*50);data=b''
 while data.count(b'Hello, World!')<50:data+=s.recv(65536)
 assert data.count(b'HTTP/1.1 200')==50
 remaining=data
 for _ in range(50):
  head,remaining=remaining.split(b'\r\n\r\n',1);length=int(next(h.split(b':',1)[1] for h in head.split(b'\r\n') if h.lower().startswith(b'content-length:')))
  assert json.loads(remaining[:length])=={'message':'Hello, World!'};remaining=remaining[length:]
 assert not remaining;s.close()
 # Abandon a large response; ensure subsequent connection still serves.
 s=socket.create_connection(('127.0.0.1',18080),timeout=10);s.sendall(b'GET /plaintext HTTP/1.1\r\nHost: local\r\n\r\n');s.close();time.sleep(.05)
 c=http.client.HTTPConnection('127.0.0.1',18080,timeout=10);c.request('GET','/json');r=c.getresponse();assert r.status==200 and json.loads(r.read())=={'message':'Hello, World!'};c.close()
 print('PASS: delayed-reader 8 MiB body; 50 pipelined JSON responses; disconnect during large response and subsequent request')
finally:p.terminate();p.wait(timeout=5)
