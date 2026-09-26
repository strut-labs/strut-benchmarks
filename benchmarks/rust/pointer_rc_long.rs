use std::sync::Arc;
fn main(){ let p=Arc::new(7i32); let mut total:i64=0; for _ in 0..50_000_000 { let q=Arc::clone(&p); total += *q as i64; } println!("{}",total); }
