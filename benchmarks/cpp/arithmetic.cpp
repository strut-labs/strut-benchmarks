#include <cstdint>
#include <iostream>

int main() {
    std::int64_t total = 0;
    for (int i = 0; i < 50000000; ++i) {
        total += i % 17;
    }
    std::cout << total << '\n';
    return 0;
}
