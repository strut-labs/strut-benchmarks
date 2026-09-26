function main() -> void {
    int_64 total := 0;
    for (int_64 i := 0; i < 200000000; i++) {
        total += (i * 31 + 7) % 97;
    }
    print(total);
    return;
}
