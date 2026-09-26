include <queue>;
function main() -> void { queue<int> q; for(int i := 0; i < 2000000; i++){ q.push(i); } int_64 sum := 0; while(!q.empty()){ sum += q.front(); q.pop(); } print(sum); }
