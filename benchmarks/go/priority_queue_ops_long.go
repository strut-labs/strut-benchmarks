package main
import("container/heap";"fmt")
type H []int
func(h H)Len()int{return len(h)}
func(h H)Less(i,j int)bool{return h[i]>h[j]}
func(h H)Swap(i,j int){h[i],h[j]=h[j],h[i]}
func(h *H)Push(x any){*h=append(*h,x.(int))}
func(h *H)Pop()any{o:=*h;n:=len(o);x:=o[n-1];*h=o[:n-1];return x}
func main(){q:=&H{};heap.Init(q);for i:=0;i<2000000;i++{heap.Push(q,i)};var s int64;for q.Len()>0{s+=int64(heap.Pop(q).(int))};fmt.Println(s)}
