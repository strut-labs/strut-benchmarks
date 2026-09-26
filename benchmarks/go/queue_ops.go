package main
import "fmt"
func main(){q:=make([]int,0,200000);for i:=0;i<200000;i++{q=append(q,i)};var s int64;for _,x:=range q{s+=int64(x)};fmt.Println(s)}
