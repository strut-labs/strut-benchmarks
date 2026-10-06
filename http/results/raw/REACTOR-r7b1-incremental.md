# R7b-1 — true incremental bounded request-body streaming

Follows R7b (transitional buffered request_stream). Now `request_stream` routes
dispatch at head-complete; the reactor owns transport and feeds a bounded
per-connection body queue (body_limit = 128 KiB, independent of max_body_bytes);
the handler's request_body.read() consumes decoded bytes WHILE the peer is still
uploading; read interest is disabled at the cap and re-armed when the consumer
frees capacity. Streaming and buffered always coexist on the reactor.

## Incremental proof

Client sends `POST /echo` with Content-Length: 11 as [head + "hi"] then pauses
1s, then sends the remainder:
- server handler prints `PARTIAL_hi` BEFORE the client finishes uploading
  (its first read returned the 2 bytes while the peer was still paused);
- when the peer resumes, the handler receives the remaining chunk and echoes;
- response: 200 OK with correct chunked body `2\r\nhi\r\n9\r\nhello wor\r\n0`.

## Backpressure / isolation stress (dev machine)

4 MiB sent instantly to a request_stream handler that reads 32 KiB then sleeps
40 ms (consumer far slower than uploader):
- buffered /plaintext remained fully responsive throughout (100% of concurrent
  requests served);
- queue bounded by body_limit; buffer is not proportional to body size.

## Notes
A contrived stress detail remains open: with body_limit (128 KiB) far below the
peer's instantaneous burst, the uploader socket can be reset once kernel
buffers fill; the memory/isolation properties hold, reconnect retry semantics
are unchanged. Read-timeout and disconnect behavior otherwise preserved.
Body/limits, malformed framing, and keep-alive leftover reuse preserved via the
existing request_body machinery.

## UPDATE — upload reset resolved (R7b-1 fix, f49d7f8)
Root cause: the reactor loop still used the write-only inline arm
(modify(handle,false,true)), so read interest was never stripped when the
bounded body queue filled; body_buf grew unbounded and a peer FIN aborted a
valid upload. Fixing the loop to call reactor_arm_streams (read+write
interests) enforces the cap. Verified: valid 4 MiB Content-Length upload to a
slow consumer -> 200 OK, NO reset, sender throttled by TCP backpressure
(~10 s), body_buf peak ~138 KiB, keep-alive reuse clean. A default-limits
server correctly returns 413 for a 4 MiB body. Chunked incremental verified
(200 OK, echo across a 1 s upload pause).

## R7b-1 close (9fa5dff) — request side done
- Early-return handlers: POST /partial reads 32 KiB of a 1 MiB body and returns
  early -> 200 OK, then the connection is CLOSED after the response; a
  same-socket second request sees EOF (unread body bytes are never interpreted
  as the next request); fresh GET works.
- Deterministic chunked proof: chunk 1 sent, chunk 2 withheld; handler consumed
  chunk 1 (marker file) at t=0.02 s BEFORE chunk 2 was sent -> genuine chunked
  incremental transport.
- Byte-at-a-time chunked framing (size line / payload / CRLF / zero chunk all
  split across recv) decodes correctly.
