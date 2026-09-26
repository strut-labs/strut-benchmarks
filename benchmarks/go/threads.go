package main

import "fmt"

func work(offset int64, out chan<- int64) {
    var total int64
    for i := int64(0); i < 10000000; i++ {
        total += (i + offset) % 17
    }
    out <- total
}

func main() {
    out := make(chan int64, 4)
    go work(0, out)
    go work(1, out)
    go work(2, out)
    go work(3, out)

    total := <-out + <-out + <-out + <-out
    fmt.Println(total)
}
