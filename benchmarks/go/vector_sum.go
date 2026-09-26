package main

import "fmt"

func main() {
    values := make([]int, 0)
    for i := 0; i < 1000000; i++ {
        values = append(values, i)
    }

    var total int64
    for _, value := range values {
        total += int64(value)
    }

    fmt.Println(total)
}
