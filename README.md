# Kubernetes Inventory Service Lab

This lab demonstrates Kubernetes Service discovery, readiness-based traffic routing, and Deployment recovery. It runs a small Inventory HTTP service with two replicas and a client Pod that calls `http://inventory/` using the Kubernetes Service DNS name.

## Architecture

```text
inventory-client Pod
        |
        | HTTP GET http://inventory/
        v
inventory Service (ClusterIP, port 80)
        |
        +------> ready Inventory Pod A:8080
        +------> ready Inventory Pod B:8080
```

Each Inventory response includes the Pod name that served it. The readiness endpoint checks `/tmp/unready`; the liveness endpoint stays healthy during the readiness demonstration, so an unready Pod remains running while Kubernetes removes it from normal Service traffic.

## Requirements

- Kubernetes cluster and `kubectl` (tested with WSL2, Docker Engine, kind, and Ubuntu).
- Docker Engine available to kind.
- `kind` and `kubectl` installed in the same environment where Docker runs.

### WSL2 setup used for this run

Inside Ubuntu WSL2, install Docker Engine and enable it:

```sh
sudo apt-get update
sudo apt-get install -y docker.io curl
sudo systemctl enable --now docker
```

Install kind and kubectl (the versions used for the included evidence):

```sh
sudo curl -fsSLo /usr/local/bin/kind https://kind.sigs.k8s.io/dl/v0.33.0/kind-linux-amd64
sudo chmod +x /usr/local/bin/kind
sudo curl -fsSLo /usr/local/bin/kubectl https://dl.k8s.io/release/v1.37.2/bin/linux/amd64/kubectl
sudo chmod +x /usr/local/bin/kubectl
```

Create the cluster and deploy from the repository directory (available in WSL under `/mnt/c/Users/<your-user>/Desktop/273`):

```sh
kind create cluster --name cmpe273
docker build -t inventory-lab:1.0 .
kind load docker-image inventory-lab:1.0 --name cmpe273
kubectl apply -f k8s/
kubectl rollout status deployment/inventory
kubectl rollout status deployment/inventory-client
kubectl get pods -o wide
kubectl get service inventory
kubectl get endpoints inventory
```

The included evidence was produced with Ubuntu 26.04 LTS on WSL2, Docker Engine 29.1.3, kind 0.33.0, Kubernetes 1.37.0, and kubectl 1.37.2.

## Show requests reaching both replicas

The client continuously calls the Service DNS name. Check its logs:

```sh
kubectl logs deployment/inventory-client --tail=20
```

The responses below name both replicas, confirming the client uses the Service and not individual Pod addresses.

## Readiness failure and recovery

Choose an Inventory Pod and induce readiness failure by creating the marker file inside that Pod:

```sh
pod=$(kubectl get pods -l app=inventory -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$pod" -- touch /tmp/unready
kubectl get pod "$pod"
kubectl get endpoints inventory
kubectl logs deployment/inventory-client --since=10s
```

After a few seconds, the Pod should still be `Running` but report `0/1`. Its endpoint disappears from the Service, and the client continues receiving responses from the remaining ready replica.

Restore readiness:

```sh
kubectl exec "$pod" -- rm /tmp/unready
kubectl wait --for=condition=Ready "pod/$pod" --timeout=30s
kubectl get endpoints inventory
kubectl logs deployment/inventory-client --since=10s
```

The Pod returns to `1/1`, reappears as a Service endpoint, and receives traffic again.

## Pod deletion and replacement

Delete one Inventory Pod and wait for the Deployment to restore two ready replicas:

```sh
old=$(kubectl get pods -l app=inventory -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$old"
kubectl rollout status deployment/inventory --timeout=90s
kubectl get pods -l app=inventory -o wide
kubectl get service inventory
kubectl logs deployment/inventory-client --since=20s
```

The Deployment creates a new Pod with a different generated name. The `inventory` Service remains unchanged, and the client continues receiving responses through `http://inventory/`.

## Evidence

The following captured terminal output is also saved as text files under [`evidence/`](evidence/). The screenshots requested for submission belong in `evidence/screenshots/`.

### Both replicas and Service traffic

```text
NAME                         READY   STATUS    IP
inventory-78fb67ddbb-bsndp   1/1     Running   10.244.0.8
inventory-78fb67ddbb-grwr8   1/1     Running   10.244.0.3

NAME        TYPE        CLUSTER-IP      PORT(S)
inventory   ClusterIP   10.96.177.132  80/TCP

NAME        ENDPOINTS
inventory   10.244.0.3:8080,10.244.0.8:8080

Client responses through http://inventory:
inventory response from inventory-78fb67ddbb-bsndp
inventory response from inventory-78fb67ddbb-grwr8
inventory response from inventory-78fb67ddbb-bsndp
inventory response from inventory-78fb67ddbb-grwr8
```

### Readiness failure

```text
=== Pod remains Running but is 0/1 ===
NAME                         READY   STATUS
inventory-78fb67ddbb-bsndp   0/1     Running

=== Service has only the other ready endpoint ===
NAME        ENDPOINTS
inventory   10.244.0.3:8080

Recent client responses:
inventory response from inventory-78fb67ddbb-grwr8
inventory response from inventory-78fb67ddbb-grwr8
inventory response from inventory-78fb67ddbb-grwr8
```

### Readiness recovery

```text
pod/inventory-78fb67ddbb-bsndp condition met

NAME                         READY   STATUS
inventory-78fb67ddbb-bsndp   1/1     Running
inventory-78fb67ddbb-grwr8   1/1     Running

NAME        ENDPOINTS
inventory   10.244.0.3:8080,10.244.0.8:8080

Client responses again include both replicas, including:
inventory response from inventory-78fb67ddbb-bsndp
```

### Pod deletion and replacement

```text
=== Delete inventory-78fb67ddbb-grwr8 ===
pod "inventory-78fb67ddbb-grwr8" deleted from default namespace
deployment "inventory" successfully rolled out

=== New two-pod state after replacement ===
NAME                         READY   STATUS    AGE
inventory-78fb67ddbb-bsndp   1/1     Running
inventory-78fb67ddbb-qcnb2   1/1     Running

=== Service name and endpoints after replacement ===
NAME        TYPE        CLUSTER-IP      PORT(S)
inventory   ClusterIP   10.96.177.132  80/TCP
inventory   10.244.0.8:8080,10.244.0.9:8080

Client responses continued through http://inventory, including:
inventory response from inventory-78fb67ddbb-bsndp
inventory response from inventory-78fb67ddbb-qcnb2
```

## Reflection

A stable Service name gives clients one dependable address even while the Pods behind it change. Kubernetes updates the Service endpoints as Pods become ready, fail readiness, or are replaced. Clients can keep calling `http://inventory` without tracking Pod IP addresses or restarting when a Pod is recreated. This separation makes recovery routine and keeps application configuration simpler.
