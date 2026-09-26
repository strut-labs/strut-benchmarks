#include <cstdint>
#include <iostream>
#include <vector>
int main(){ std::vector<int> values; values.reserve(1000000); for(int i=0;i<1000000;i++) values.push_back(i); auto fn=[](int x){return x*2;}; std::vector<int> doubled; doubled.reserve(values.size()); for(int x:values) doubled.push_back(fn(x)); std::int64_t total=0; for(int x:doubled) total+=x; std::cout<<total<<'\n'; }
