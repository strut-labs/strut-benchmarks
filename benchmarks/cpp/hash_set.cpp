#include <iostream>
#include <unordered_set>
int main(){std::unordered_set<int> s; for(int i=0;i<200000;++i)s.insert(i); int n=0; for(int i=0;i<200000;++i)n+=s.contains(i); std::cout<<n<<"\n";}
