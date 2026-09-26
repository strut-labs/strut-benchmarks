#include <cstdint>
#include <iostream>
#include <vector>

int main() {
    std::vector<int> values;
    for (int i = 0; i < 1000000; ++i) {
        values.push_back(i);
    }

    std::int64_t total = 0;
    for (int value : values) {
        total += value;
    }

    std::cout << total << '\n';
    return 0;
}
