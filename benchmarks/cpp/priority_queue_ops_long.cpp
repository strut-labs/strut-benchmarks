#include <iostream>
#include <queue>
int main(){std::priority_queue<int> q; for(int i=0;i<2000000;++i)q.push(i); long long s=0; while(!q.empty()){s+=q.top();q.pop();} std::cout<<s<<"\n";}
