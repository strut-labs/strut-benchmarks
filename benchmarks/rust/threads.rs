fn work(offset: i64) -> i64 {
    let mut total = 0i64;
    for i in 0..10_000_000i64 {
        total += (i + offset) % 17;
    }
    total
}

fn main() {
    let a = std::thread::spawn(|| work(0));
    let b = std::thread::spawn(|| work(1));
    let c = std::thread::spawn(|| work(2));
    let d = std::thread::spawn(|| work(3));

    let total = a.join().unwrap()
        + b.join().unwrap()
        + c.join().unwrap()
        + d.join().unwrap();

    println!("{total}");
}
