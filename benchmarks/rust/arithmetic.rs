fn main() {
    let mut total: i64 = 0;
    for i in 0..50_000_000i64 {
        total += i % 17;
    }
    println!("{total}");
}
