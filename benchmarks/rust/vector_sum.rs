fn main() {
    let mut values: Vec<i32> = Vec::new();
    for i in 0..1_000_000 {
        values.push(i);
    }

    let mut total: i64 = 0;
    for value in values {
        total += value as i64;
    }

    println!("{total}");
}
