include <vector>;
function main() -> void {
    int[] values := [];
    values.reserve(1000000);
    for (int i := 0; i < 1000000; i++) {
        values.push(i);
    }
    doubled := values.map((int x) => x * 2);
    int_64 total := 0;
    for (x : doubled) {
        total += x;
    }
    print(total);
    return;
}
