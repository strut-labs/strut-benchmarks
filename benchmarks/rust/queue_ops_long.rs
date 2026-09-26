use std::collections::VecDeque; fn main(){let mut q=VecDeque::new();for i in 0i32..2000000{q.push_back(i);}let mut s:i64=0;while let Some(x)=q.pop_front(){s+=x as i64;}println!("{}",s);}
