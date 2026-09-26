include <vector>;
function main() -> void {
    int[] values := [];
    for (int i := 0; i < 1000000; i++) {
        values.push(i);
    }

    int_64 total := 0;
    for (value : values) {
        total = total + value;
    }

    print(total);
    return;
}
