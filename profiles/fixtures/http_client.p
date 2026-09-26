function main() -> void : HttpError {
    response := http_get("http://127.0.0.1:9/");
    print(response.status);
    return;
}
