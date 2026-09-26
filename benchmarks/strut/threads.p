function work(int offset, int* result) -> void {
    int total := 0;
    for (int i := 0; i < 10000000; i++) {
        total = total + (i + offset) % 17;
    }
    *result = total;
    return;
}

function main() -> void : ThreadError {
    a := ptr(0);
    b := ptr(0);
    c := ptr(0);
    d := ptr(0);

    ta := thread(() => { work(0, a); });
    tb := thread(() => { work(1, b); });
    tc := thread(() => { work(2, c); });
    td := thread(() => { work(3, d); });

    ta.join();
    tb.join();
    tc.join();
    td.join();

    print(*a + *b + *c + *d);
    return;
}
