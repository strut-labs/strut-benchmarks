package main

import "fmt"

func main() {
    var total int64
    for i := int64(0); i < 50000000; i++ {
        total += i % 17
    }
    fmt.Println(total)
}
