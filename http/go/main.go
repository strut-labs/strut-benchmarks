package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"runtime"
)

func plaintext(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.Write([]byte("Hello, World!"))
}

func jsonHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	body, _ := json.Marshal(map[string]string{"message": "Hello, World!"})
	w.Write(body)
}

func main() {
	fmt.Fprintf(os.Stderr, "config gomaxprocs=%d numcpu=%d\n", runtime.GOMAXPROCS(0), runtime.NumCPU())
	mux := http.NewServeMux()
	mux.HandleFunc("/plaintext", plaintext)
	mux.HandleFunc("/json", jsonHandler)
	srv := &http.Server{Addr: "0.0.0.0:8080", Handler: mux}
	if err := srv.ListenAndServe(); err != nil {
		panic(err)
	}
}
