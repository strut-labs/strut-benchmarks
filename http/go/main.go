package main

import (
	"encoding/json"
	"net/http"
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
	mux := http.NewServeMux()
	mux.HandleFunc("/plaintext", plaintext)
	mux.HandleFunc("/json", jsonHandler)
	srv := &http.Server{Addr: "0.0.0.0:8080", Handler: mux}
	if err := srv.ListenAndServe(); err != nil {
		panic(err)
	}
}
