package main
import "fmt"
func main(){q:=make([]int,0,2000000);for i:=0;i<2000000;i++{q=append(q,i)};var s int64;for _,x:=range q{s+=int64(x)};fmt.Println(s)}
