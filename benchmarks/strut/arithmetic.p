function main() -> void {
    int_64 total := 0;
    for (int i := 0; i < 50000000; i++) {
        total = total + i % 17;
    }
    print(total);
    return;
}
