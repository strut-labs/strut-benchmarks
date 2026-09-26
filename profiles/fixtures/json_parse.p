function main() -> void {
    text := "{\"name\":\"strut\",\"values\":[1,2,3,4],\"active\":true}";
    encoded := "";
    for (int i := 0; i < 100000; i++) {
        value := json.parse(text);
        encoded = json.stringify(value);
    }
    print(encoded);
    return;
}
