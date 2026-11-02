# Kubernetes Service Discovery, Readiness, and Recovery Lab

This lab runs a tiny Inventory HTTP service with two replicas and a client that calls the stable Kubernetes Service DNS name `inventory`.

## Architecture

```text
inventory-client Pod
        |
        | HTTP to http://inventory (Service DNS)
        v
inventory Service (ClusterIP, port 80)
        |
        +------> inventory Pod A:8080
        +------> inventory Pod B:8080
```

The Service selects Pods labeled `app: inventory` and only routes normal traffic to ready endpoints. Each response includes the serving Pod name. The readiness endpoint checks a local marker file; the liveness endpoint remains healthy when readiness is deliberately failed, so the Pod stays running.

## Prerequisites

- A working Kubernetes cluster and `kubectl` configured for it (Minikube, kind, or Docker Desktop Kubernetes).
- Docker or another way to build and load the image into the cluster. For a local Minikube/kind cluster, build with Docker and load the image as shown below.

## Deploy

From the repository root:

```sh
docker build -t inventory-lab:1.0 .
# For Minikube:
minikube image load inventory-lab:1.0
# For kind, use this instead:
# kind load docker-image inventory-lab:1.0

kubectl apply -f k8s/
kubectl rollout status deployment/inventory
kubectl rollout status deployment/inventory-client
kubectl get pods -o wide
kubectl get service inventory
kubectl get endpoints inventory
```

Expected starting state: two `inventory` Pods report `1/1 Running`; the `inventory` Service has two endpoints; one client Pod is running.

## Show requests reaching both replicas

Read the client log. Each line names the Inventory Pod that answered, and the client uses the Service name (not a Pod IP):

```sh
kubectl logs deployment/inventory-client --tail=20
```

Capture the output in the evidence section below. Across repeated requests, both inventory Pod names should appear.

## Readiness failure and recovery

Choose one Inventory Pod and save its name:

```sh
$pod = kubectl get pods -l app=inventory -o jsonpath='{.items[0].metadata.name}'
```

Make its readiness check fail by creating the marker file inside that Pod. This does not stop the process, and `/health` continues to pass:

```sh
kubectl exec $pod -- touch /tmp/unready
kubectl get pod $pod
kubectl get endpoints inventory
kubectl logs deployment/inventory-client --tail=20
```

Wait for the probe interval (up to a few seconds). The chosen Pod should remain `Running` but become `0/1`; its address should disappear from the Service endpoints, and client output should contain only the other ready Pod name.

Restore readiness:

```sh
kubectl exec $pod -- rm /tmp/unready
kubectl wait --for=condition=Ready pod/$pod --timeout=30s
kubectl get endpoints inventory
kubectl logs deployment/inventory-client --tail=20
```

The Pod should become `1/1` again, return as a Service endpoint, and appear in subsequent client responses.

## Pod deletion and replacement

Record the current Pod names, delete one Inventory Pod, and observe its replacement:

```sh
kubectl get pods -l app=inventory -o wide
$old = kubectl get pods -l app=inventory -o jsonpath='{.items[0].metadata.name}'
kubectl delete pod $old
kubectl get pods -l app=inventory -w
```

Stop watching after the replacement reaches `Running` and `Ready` (Ctrl-C), then confirm:

```sh
kubectl get pods -l app=inventory -o wide
kubectl get service inventory
kubectl logs deployment/inventory-client --tail=20
```

The Deployment creates a Pod with a different generated name. The Service remains named `inventory`, and client requests continue through `http://inventory` as endpoints change.

## Evidence

Paste real terminal output or add screenshots captured during your run. These sections are intentionally ready to fill with your cluster's output.

### Both replicas receive requests

```text
[Paste `kubectl get pods -l app=inventory` and client log output showing both Pod names here]
```

### Readiness failure and recovery

```text
[Paste output showing the selected Pod Running but 0/1, its removal from Service endpoints,
client requests reaching only the other Pod, then Ready status and traffic returning here]
```

### Pod deletion and replacement

```text
[Paste the old Pod name, deletion result, new Pod name, unchanged Service name, and continued client output here]
```

## Reflection

A stable Service name gives clients one dependable address even while the Pods behind it change. Kubernetes updates the Service's endpoints as Pods become ready, fail readiness, or are replaced. Clients can keep calling `http://inventory` without tracking Pod IP addresses or restarting when a Pod is recreated. This separation makes recovery routine and keeps application configuration simpler.
