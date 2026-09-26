async function twice(int x) -> int {
    return x * 2;
}
function main() -> void {
    int_64 total := 0;
    for (int i := 0; i < 10000; i++) {
        pending := twice(i);
        total += await pending;
    }
    print(total);
    return;
}
