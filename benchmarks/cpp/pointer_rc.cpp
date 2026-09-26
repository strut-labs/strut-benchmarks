#include <cstdint>
#include <iostream>
#include <memory>
int main(){ auto p=std::make_shared<int>(7); std::int64_t total=0; for(int i=0;i<5000000;i++){ auto q=p; total+=*q; } std::cout<<total<<'\n'; }
