atomic<int> counter := 0;

function increment() -> void {
    for (int i := 0; i < 250000; i++) {
        counter.fetch_add(1);
    }
    return;
}

function main() -> int : ThreadError {
    a := thread(increment);
    b := thread(increment);
    c := thread(increment);
    d := thread(increment);
    a.join();
    b.join();
    c.join();
    d.join();
    print(counter.load());
    return 0;
}
