include <ordered_map>;
function main() -> void { ordered_map<int,int> m; for(int i := 0; i < 200000; i++){ m.insert(i,i); } int_64 sum := 0; for(int i := 0; i < 200000; i++){ sum += m[i]; } print(sum); }
