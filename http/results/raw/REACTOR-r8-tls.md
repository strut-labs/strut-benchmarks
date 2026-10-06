# R8 — reactor-native TLS

listen_tls now routes to the reactor path under STRUT_HTTP_REACTOR=1. Each TLS
connection carries an SSL*; SSL_accept / SSL_read / SSL_write run on the
nonblocking fd with SSL_ERROR_WANT_READ / WANT_WRITE mapped to reactor
readable / writable interests. OpenSSL is never run on the application worker.
Incremental handshake steps on readiness events; tls_want_write arms write
interest; AUTO_RETRY set on the context. Streaming/request/WebSocket adapters
operate over the TLS transport unchanged; plaintext path falls through to raw
nonblocking I/O.

## Validated (python ssl client, self-signed cert; dev 20-core, STRUT_HTTP_REACTOR=1)
- handshake + 200 OK over TLS
- keep-alive: 3 requests on one TLS connection
- a no-data handshake peer, and a byte-at-a-time handshake peer, do NOT block
  20 concurrent fast TLS requests (all 200 OK)
- reactor threads bounded (37 = reactor + app + stream on dev; 1-vCPU to be
  re-measured at R8.5 rebenchmark)

## Certification
CTest 16/16 x4 (GCC/Clang -Werror, ASan/UBSan), regressions 288/288 both modes,
codegen pass, git diff --check clean. Plaintext reactor path unchanged (no TLS
cost when TLS unused).

Next: R8.5 early-R13 Linux request hot-path performance campaign.

## R8 focused certification (local) - all gaps closed
- invalid TLS (plain HTTP to TLS port, garbage bytes): closed immediately (~0ms,
  fixed in follow-up), normal TLS unaffected
- disconnect mid-handshake (partial ClientHello) and connect+no-data: safe, recovered
- handshake timeout: a no-data handshake is closed by the server (idle deadline)
- partial SSL_write: 4 MiB encrypted response to a stalled reader; concurrent
  normal TLS requests all 200 OK
- partial SSL_read / slow upload: request_stream over TLS, 2 bytes then 1s pause,
  then remainder -> 200 OK
- WSS: 101 upgrade + text echo through the reactor TLS transport
- Reactor stop()/drain with a TLS server: STOP_OK, joins cleanly
- reactor thread count bounded throughout
