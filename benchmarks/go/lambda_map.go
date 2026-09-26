package main
import "fmt"
func main(){ values:=make([]int,0,1000000); for i:=0;i<1000000;i++ { values=append(values,i) }; fn:=func(x int) int { return x*2 }; doubled:=make([]int,0,len(values)); for _,x:=range values { doubled=append(doubled,fn(x)) }; var total int64; for _,x:=range doubled { total+=int64(x) }; fmt.Println(total) }
