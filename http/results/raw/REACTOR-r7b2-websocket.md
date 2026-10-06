# R7b-2 — WebSocket on the reactor (R7 complete)

WebSocket routes now run on the reactor path (no whole-server legacy fallback).
The existing strut_websocket framing/API is unchanged; transport callbacks are
reactor adapters: inbound via the bounded body queue (read interest off at the
cap, re-armed as the app consumes), outbound via the bounded output queue
drained on writable readiness. The ws handler runs on the bounded stream-worker
pool.

Verified (hand-rolled WS client / handshake+frames):
- Upgrade 101 Switching Protocols
- masked text echo (opcode 1, payload round-trips)
- close handshake
- idle ws survives (no read-timeout kill)

Linode 1-vCPU (STRUT_HTTP_REACTOR=1):
- 40 idle websockets -> native threads stay at 6
  (reactor + 1 app worker + 4 stream workers), RSS ~4.6 MB
  => no native thread per WebSocket
- buffered /plaintext and /json coexist with ws routes.
- ws route now registers method GET; STRUT_USE_WEBSOCKET guards keep non-ws
  servers byte-identical.

## R7 status: COMPLETE
response streaming (R7a), true incremental request streaming (R7b-1), and
WebSocket (R7b-2) are all reactor-native with bounded adapters; buffered path
remains healthy (~16k plaintext c=50). Next: R8 reactor-native TLS.

## Ledger
~1.2k original -> ~9k TCP_NODELAY -> ~11-12k reactor -> ~16.8k writev reactor
-> R7a 16.8k -> R7b 16k (variance). Perf medians to be re-recorded at R8.5.

## Evidence classification (keep accurate)
- The permanent regression fixture (`reactor-websocket-test`, STRUT_HTTP_REACTOR=1)
  proves only: a WebSocket route coexists with buffered HTTP on the reactor path,
  the server starts, /plaintext is served, stop()/join works.
- The stronger WebSocket claims (101 handshake, masked text echo, close
  handshake, idle-WebSocket survival, and the 40-idle-WebSocket -> 6-thread
  bounded proof) come from the focused/hand-rolled client and Linode
  certification tests recorded above. Do not attribute those to the fixture.
