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
