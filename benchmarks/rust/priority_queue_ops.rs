use std::collections::BinaryHeap; fn main(){let mut q=BinaryHeap::new();for i in 0i32..200000{q.push(i);}let mut s:i64=0;while let Some(x)=q.pop(){s+=x as i64;}println!("{}",s);}
