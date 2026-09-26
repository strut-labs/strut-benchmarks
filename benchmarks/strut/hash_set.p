include <set>;
function main() -> void { set<int> s; for(int i := 0; i < 200000; i++){ s.add(i); } int n := 0; for(int i := 0; i < 200000; i++){ if(s.contains(i)){ n += 1; } } print(n); }
