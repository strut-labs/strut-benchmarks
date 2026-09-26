#include <iostream>
#include <map>
int main(){std::map<int,int> m; for(int i=0;i<200000;++i)m.emplace(i,i); long long s=0; for(int i=0;i<200000;++i)s+=m.at(i); std::cout<<s<<"\n";}
