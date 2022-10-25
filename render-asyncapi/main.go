package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/nats-io/nats.go"
)

type Handler struct {
	nc       *nats.Conn
	rootPath string
}

func (h *Handler) asyncAPISchemaHandler(w http.ResponseWriter, req *http.Request) {
	data := map[string]interface{}{"jsonrpc": "2.0", "id": "ad1f2612-4f11-4667-bf7d-d20c2b5c8285", "params": map[string]string{}}
	payload, _ := json.Marshal(data)
	path := h.rootPath + ".schema.RETRIEVE"
	reply_raw, err := h.nc.Request(path, payload, 500*time.Millisecond)

	if err != nil {
		// If not head is not 200, html generator will not work and display the error
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `
        {
            "asyncapi": "2.0",
            "info": {
                "title": "ERROR",
                "description": "<p style='color: red'>%s</p><p style='color: red'>Full subject: '%s'</p>",
            },
            "channels": {}
        }
        `, err.Error(), path)
		return
	}

	reply := make(map[string]interface{})
	json_err := json.Unmarshal(reply_raw.Data, &reply)

	schema, _ := json.Marshal(reply["result"])

	if reply["result"] == nil || json_err != nil {
		// If not head is not 200, html generator will not work and display the error
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `
        {
            "asyncapi": "2.0",
            "info": {
                "title": "ERROR",
                "description": "<p style='color: red'>Was able to get reply from NATS service, but not able to retrieve schema. Make sure you pass the correct root path as an argument.</p><p style='color: red'>Your full path is: '%s'</p>",
            },
            "channels": {}
        }
        `, path)
		return
	}
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "%s", schema)
}

func asyncAPIRedocHandler(w http.ResponseWriter, req *http.Request) {
	w.WriteHeader(http.StatusOK)

	fmt.Fprintf(w, `
    <body>
        <redoc spec-url='http://localhost:8090/asyncapi.json'></redoc>
        <script src='https://raw.githubusercontent.com/wegroupwolves/natsapi/master/render-asyncapi/redoc.asyncapi.js'></script>
    </body>
    `)
}

func main() {
	if len(os.Args) < 2 {
		log.Fatal("No natsport and root path given, should be `./app 4222 master.service-staging`")
	}
	natsPort := os.Args[1]
	rootPath := os.Args[2]

	nc, err := nats.Connect("nats://127.0.0.1:" + natsPort)
	if err != nil {
		log.Fatal(err)
	}
	h := &Handler{nc: nc, rootPath: rootPath}

	http.HandleFunc("/asyncapi.json", h.asyncAPISchemaHandler)
	http.HandleFunc("/", asyncAPIRedocHandler)

	fmt.Println("Server running")
	fmt.Println("Docs can be found on localhost:8090")
	fmt.Println("Connected to nats on port " + natsPort)
	http.ListenAndServe(":8090", nil)
}
