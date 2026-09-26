package main
import "fmt"
func main(){ var total int64; for i:=int64(0); i<200000000; i++ { total += (i*31+7)%97 }; fmt.Println(total) }
