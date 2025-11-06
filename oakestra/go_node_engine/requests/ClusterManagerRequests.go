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

/////////////////// GRACEFUL EXIT ///////////////////

// HandshakeAnswer is the struct that describes the handshake answer between the nodes
type ClusterHandshakeAnswer struct {
	MqttPort string `json:"MQTT_BROKER_PORT"`
	NodeId   string `json:"id"`
}

// // Sent to the cluster manager upon exit decision
type ClusterExitRequest struct {
	NodeId     string `json:"node_id"`
	ExitStatus string `json:"exit_status"`
	Jobs       []Job  `json:"jobs"`
}

type ClusterExitResponse struct {
	Message string `json:"message"`
}

/////////////////// HEURISTICS ///////////////////

// Negotiation Structs
type NegotiationRequest struct {
	NodeId string `json:"node_id"`
	Jobs   []Job  `json:"jobs"`
}

type Job struct {
	JobID          string `json:"job_id"`
	JobName        string `json:"job_name"`
	InstanceNumber int    `json:"instance"`
}

type NegotiationResponse struct {
	Decisions []JobDecision `json:"decisions"`
}

type JobDecision struct {
	JobName  string `json:"job_name"`
	Decision string `json:"decision"`
}

// Exit Confirmation Structs
type ExitConfirmationRequest struct {
	Message string `json:"message"`
}

type ExitConfirmaionResponse struct {
	Message string `json:"message"`
}

//////////////////////////////////////////////////

func ClusterHandshake(address string, port int) ClusterHandshakeAnswer {
	// This function sends a handshake request to the cluster manager
	// after the root has responded with its information.
	data, err := json.Marshal(model.GetNodeInfo())
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, json encoding problem, %v", err)
	}
	jsonbody := bytes.NewBuffer(data)
	resp, err := http.Post(fmt.Sprintf("http://%s:%d/api/node/register", address, port), "application/json", jsonbody)
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

	handshakeAnswer := ClusterHandshakeAnswer{}
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

func NotifyClusterExit(address string, port int, node_id string, jobs []Job) ClusterExitResponse {
	// This is the function to used to notify the cluster orchestrator of a worker exit
	// in the "Naive" and "Improved" solutions.
	request := ClusterExitRequest{
		NodeId: node_id,
		Jobs:   jobs,
	}

	data, err := json.Marshal(request)
	if err != nil {
		logger.ErrorLogger().Fatalf("Exit request failed, json encoding problem, %v", err)
	}
	jsonbody := bytes.NewBuffer(data)

	resp, err := http.Post(fmt.Sprintf("http://%s:%d/api/node/request_exit", address, port), "application/json", jsonbody)
	if err != nil {
		logger.ErrorLogger().Fatalf("Exit request failed, %v", err)
	}
	if resp.StatusCode != 200 {
		logger.ErrorLogger().Fatalf("Exit request failed with error code %d", resp.StatusCode)
	}

	defer func() {
		if err := resp.Body.Close(); err != nil {
			logger.ErrorLogger().Fatalf("Exit request failed, %v", err)
		}
	}()

	exitResponse := ClusterExitResponse{}
	responseBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, %v", err)
	}
	err = json.Unmarshal(responseBytes, &exitResponse)
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, %v", err)
	}
	return exitResponse
}

func Negotiate(address string, port int, node_id string, jobs []Job) NegotiationResponse {
	// This function sends the running jobs to the cluster orchestrator and receives a list
	// of keep/kill decisions for each of the jobs.
	request := NegotiationRequest{
		NodeId: node_id,
		Jobs:   jobs,
	}

	data, err := json.Marshal(request)
	if err != nil {
		logger.ErrorLogger().Fatalf("Exit request failed, json encoding problem, %v", err)
	}
	jsonbody := bytes.NewBuffer(data)

	resp, err := http.Post(fmt.Sprintf("http://%s:%d/api/node/negotiate_exit", address, port), "application/json", jsonbody)
	if err != nil {
		logger.ErrorLogger().Fatalf("Exit request failed, %v", err)
	}
	if resp.StatusCode != 200 {
		logger.ErrorLogger().Fatalf("Exit request failed with error code %d", resp.StatusCode)
	}

	defer func() {
		if err := resp.Body.Close(); err != nil {
			logger.ErrorLogger().Fatalf("Exit request failed, %v", err)
		}
	}()

	// Parsing Response
	negotiationResponse := NegotiationResponse{}

	responseBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, %v", err)
	}

	err = json.Unmarshal(responseBytes, &negotiationResponse)
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, %v", err)
	}

	fmt.Println("NEGOTIATION RESPONSE:", negotiationResponse.Decisions)
	return negotiationResponse
}

func ConfirmExit(address string, port int, node_id string) {
	data, err := json.Marshal(model.GetNodeInfo())
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, json encoding problem, %v", err)
	}
	jsonbody := bytes.NewBuffer(data)
	resp, err := http.Post(fmt.Sprintf("http://%s:%d/api/node/confirm_exit", address, port), "application/json", jsonbody)
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

	handshakeAnswer := ClusterHandshakeAnswer{}
	responseBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, %v", err)
	}
	err = json.Unmarshal(responseBytes, &handshakeAnswer)
	if err != nil {
		logger.ErrorLogger().Fatalf("Handshake failed, %v", err)
	}
}
