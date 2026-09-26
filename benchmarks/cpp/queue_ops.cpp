#include <iostream>
#include <queue>
int main(){std::queue<int> q; for(int i=0;i<200000;++i)q.push(i); long long s=0; while(!q.empty()){s+=q.front();q.pop();} std::cout<<s<<"\n";}
