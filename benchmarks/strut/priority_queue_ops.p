include <priority_queue>;
function main() -> void { priority_queue<int> q; for(int i := 0; i < 200000; i++){ q.push(i); } int_64 sum := 0; while(!q.empty()){ sum += q.top(); q.pop(); } print(sum); }
