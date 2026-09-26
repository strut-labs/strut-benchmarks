fn main(){ let mut total:i64=0; for i in 0i64..200_000_000i64 { total += (i*31+7)%97; } println!("{}",total); }
