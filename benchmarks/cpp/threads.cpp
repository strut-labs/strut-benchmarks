#include <cstdint>
#include <iostream>
#include <thread>

void work(int offset, std::int64_t* result) {
    std::int64_t total = 0;
    for (int i = 0; i < 10000000; ++i) {
        total += (i + offset) % 17;
    }
    *result = total;
}

int main() {
    std::int64_t a = 0, b = 0, c = 0, d = 0;
    std::thread ta(work, 0, &a);
    std::thread tb(work, 1, &b);
    std::thread tc(work, 2, &c);
    std::thread td(work, 3, &d);

    ta.join();
    tb.join();
    tc.join();
    td.join();

    std::cout << a + b + c + d << '\n';
    return 0;
}
