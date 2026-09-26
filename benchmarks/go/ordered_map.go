package main
import "fmt"
func main(){m:=make(map[int]int,200000);for i:=0;i<200000;i++{m[i]=i};var s int64;for i:=0;i<200000;i++{s+=int64(m[i])};fmt.Println(s)}
