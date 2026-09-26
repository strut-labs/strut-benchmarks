fn main(){ let values:Vec<i32>=(0..1_000_000).collect(); let doubled:Vec<i32>=values.iter().map(|x| x*2).collect(); let total:i64=doubled.iter().map(|&x| x as i64).sum(); println!("{}",total); }
