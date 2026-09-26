package main
import "fmt"
func main(){m:=make(map[int]struct{},200000);for i:=0;i<200000;i++{m[i]=struct{}{}};n:=0;for i:=0;i<200000;i++{if _,ok:=m[i];ok{n++}};fmt.Println(n)}
