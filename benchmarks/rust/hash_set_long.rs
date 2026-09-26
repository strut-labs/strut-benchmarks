use std::collections::HashSet; fn main(){let mut s=HashSet::new();for i in 0i32..2000000{s.insert(i);}let mut n=0;for i in 0i32..2000000{if s.contains(&i){n+=1;}}println!("{}",n);}
