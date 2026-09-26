#include <cstdint>
#include <iostream>
int main(){ std::int64_t total=0; for(std::int64_t i=0;i<200000000;i++) total += (i*31+7)%97; std::cout<<total<<'\n'; }
