package main
import "fmt"
func main(){ v:=7; p:=&v; var total int64; for i:=0;i<50000000;i++ { q:=p; total+=int64(*q) }; fmt.Println(total) }
