int* counter := new(0);
mutex counter_mutex;

function increment() -> void {
    for (int i := 0; i < 250000; i++) {
        counter_mutex.lock(() => { *counter = *counter + 1; });
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
    print(*counter);
    return 0;
}
