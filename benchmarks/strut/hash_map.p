include <map>;
function main() -> void { map<int,int> m; for(int i := 0; i < 200000; i++){ m.insert(i,i); } int_64 sum := 0; for(int i := 0; i < 200000; i++){ sum += m[i]; } print(sum); }
