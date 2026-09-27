function main() -> void {
    int* p := new(7);
    int_64 total := 0;
    for (int i := 0; i < 5000000; i++) {
        int* q := p;
        total += *q;
    }
    print(total);
    return;
}
