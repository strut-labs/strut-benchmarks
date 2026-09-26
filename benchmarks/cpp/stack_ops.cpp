#include <iostream>
#include <stack>
int main(){std::stack<int> q; for(int i=0;i<200000;++i)q.push(i); long long s=0; while(!q.empty()){s+=q.top();q.pop();} std::cout<<s<<"\n";}
