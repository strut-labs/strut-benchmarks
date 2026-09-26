function main() -> void : NetworkError {
    http_server app := http_server();
    app.get("/hello", (http_request req) => {
        return http_text("hello, world!");
    });
    app.listen("127.0.0.1", 18091, 500000);
    return;
}
