use std::collections::BTreeMap; fn main(){let mut m=BTreeMap::new();for i in 0i32..200000{m.insert(i,i);}let mut s:i64=0;for i in 0i32..200000{s+=*m.get(&i).unwrap() as i64;}println!("{}",s);}
