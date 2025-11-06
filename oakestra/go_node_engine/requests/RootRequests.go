package requests

import (
	"bytes"
	"encoding/json"
	"fmt"
	"go_node_engine/logger"
	"go_node_engine/model"
	"io"
	"net/http"
)

// IP + Port of the cluster which the root determined the worker should connect to
type RootHandshakeAnswer struct {
	ClusterManagerAddr string `json:"cluster_manager_addr"`
	ClusterManagerPort int    `json:"cluster_manager_port"`
}

// ClusterHandshake sends a handshake request to the cluster manager
func RootHandshake(address string, port int) RootHandshakeAnswer {
	// Initial handshake with root orchestrator upon worker join.

	data, err := json.Marshal(model.GetNodeInfo())
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, json encoding problem, %v", err)
	}
	jsonbody := bytes.NewBuffer(data)
	resp, err := http.Post(fmt.Sprintf("http://%s:%d/api/dynamic/register_intent", address, port), "application/json", jsonbody) //WHICH PORT TO SEND TO?
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, %v", err)
	}
	if resp.StatusCode != 200 {
		logger.ErrorLogger().Fatalf("Handshake failed with error code %d", resp.StatusCode)
	}
	//defer resp.Body.Close()
	defer func() {
		if err := resp.Body.Close(); err != nil {
			logger.ErrorLogger().Fatalf("Handshake failed, %v", err)
		}
	}()

	handshakeAnswer := RootHandshakeAnswer{}
	responseBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, %v", err)
	}
	err = json.Unmarshal(responseBytes, &handshakeAnswer)
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, %v", err)
	}
	return handshakeAnswer
}
