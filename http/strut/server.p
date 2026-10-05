function main() -> int : NetworkError {
    app := http_server();
    app.get("/plaintext", (http_request request) => {
        return http_text("Hello, World!");
    });
    app.get("/json", (http_request request) => {
        return http_json_response({"message": "Hello, World!"});
    });
    app.listen("0.0.0.0", 8080);
    return 0;
}
