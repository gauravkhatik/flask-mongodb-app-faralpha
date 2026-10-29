# Flask and MongoDB on Kubernetes using Minikube

## 1. Project Overview

This project deploys a Flask REST API and MongoDB on a local Kubernetes cluster using Minikube. It demonstrates Docker image creation, Kubernetes Deployments and Services, persistent storage, resource requests and limits, Kubernetes DNS, and Horizontal Pod Autoscaling (HPA).

### Technology Stack

- Python 3.10
- Flask
- MongoDB
- Docker
- Kubernetes
- Minikube and kubectl
- Kubernetes Metrics Server

## 2. Project Structure

```text
flask-mongodb-app/
├── app.py
├── Dockerfile
├── requirements.txt
├── .dockerignore
├── .env.example
├── README.md
└── k8s/
    └── app.yaml
```

The Kubernetes resources can be kept together in `k8s/app.yaml` as multiple YAML documents separated by `---`. Separate YAML files are also acceptable, provided all required resources are included.

## 3. Application Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Returns a welcome message and current time |
| GET | `/data` | Returns documents stored in MongoDB |
| POST | `/data` | Inserts a JSON document into MongoDB |

The Flask application listens on port `5000`.

## 4. Prerequisites

Install Docker Desktop, Minikube, and kubectl. Verify the tools:

```bash
docker --version
minikube version
kubectl version --client
```

## 5. Build the Docker Image

Run these commands from the project root directory:

```bash
docker build -t flask-mongodb-app:latest .
docker images
```

Load the image into Minikube so the cluster can use the locally built image:

```bash
minikube start
minikube image load flask-mongodb-app:latest
```

Make sure the Flask Deployment in `k8s/app.yaml` uses `flask-mongodb-app:latest` and an appropriate local image pull policy, such as `IfNotPresent`.

### Optional: Push the Image to Docker Hub


```bash
docker login
docker tag flask-mongodb-app:latest gauravkhatik/flask-mongodb-app:latest
docker push gauravkhatik/flask-mongodb-app:latest
```

If using the registry image in Kubernetes, update the image field in the Flask Deployment manifest to the full Docker Hub image name.

## 6. Configure MongoDB Credentials

The Kubernetes Secret used in this setup is named `mongodb-secret`. The expected keys are:

- `MONGO_INITDB_ROOT_USERNAME`
- `MONGO_INITDB_ROOT_PASSWORD`
- `MONGODB_URI`

The test environment used the username `Admin`. The password used during testing contained a special character, so it must be URL-encoded when included in a MongoDB URI. For example, `@` becomes `%40`.

Use this URI pattern, substituting your configured values:

```text
mongodb://USERNAME:URL_ENCODED_PASSWORD@mongodb:27017/flask_db?authSource=admin
```

The hostname `mongodb` is the Kubernetes Service name. The Flask app reads the URI from the `MONGODB_URI` environment variable.

**Security:** Do not commit real passwords to Git or include them in a public submission. For a public repository, keep only placeholders in `.env.example` and create the Secret separately. Kubernetes Secrets are base64-encoded by default; base64 encoding is not encryption.

## 7. Deploy to Kubernetes

Start Minikube and verify the node:

```bash
minikube start
kubectl get nodes
```

Enable the Metrics Server for CPU-based HPA:

```bash
minikube addons enable metrics-server
kubectl top nodes
```

If `kubectl top nodes` initially reports that metrics are unavailable, wait a short time and try again after the Metrics Server is ready.

Create the `mongodb-secret` Secret with the three keys listed above if it is not already created by your manifest. Then apply the Kubernetes manifest:

```bash
kubectl apply -f k8s/app.yaml
```

Check the resources:

```bash
kubectl get pods
kubectl get deployments
kubectl get services
kubectl get statefulsets
kubectl get pvc
kubectl get hpa
```

Wait until the Flask pods and MongoDB pod are ready.

## 8. Access and Test the Application

Forward the Flask Service to your local machine:

```bash
kubectl port-forward service/flask-service 8080:5000
```

Keep this command running in a terminal. Open `http://localhost:8080/` in a browser.

Check stored data:

```bash
curl http://localhost:8080/data
```

Insert a sample JSON document:

```bash
curl -X POST http://localhost:8080/data \
  -H "Content-Type: application/json" \
  -d '{"sampleKey":"Gaurav"}'
```

Expected response:

```json
{
  "status": "Data inserted"
}
```

The POST endpoint should return HTTP `201 Created`. Retrieve the data again:

```bash
curl http://localhost:8080/data
```

The inserted document should appear in the returned JSON array. The sample key and value are demonstration data and can be changed.

## 9. Kubernetes DNS and Service Communication

Kubernetes provides DNS records for Services. The Flask application connects to MongoDB through the Service hostname `mongodb`, rather than using a pod IP address.

The URI follows this pattern:

```text
mongodb://USERNAME:URL_ENCODED_PASSWORD@mongodb:27017/flask_db?authSource=admin
```

Kubernetes DNS resolves `mongodb` to the ClusterIP of the MongoDB Service, and the Service routes traffic to its selected MongoDB pod.

Test name resolution from a Flask pod:

```bash
kubectl exec deployment/flask-app -- python -c "import socket; print(socket.gethostbyname('mongodb'))"
```

This command assumes the Flask Deployment is named `flask-app`.

## 10. Persistent Storage

MongoDB uses a PersistentVolumeClaim (PVC) named `mongodb-pvc` requesting `1Gi` of storage. Check its status:

```bash
kubectl get pvc
kubectl describe pvc mongodb-pvc
```

The expected status is `Bound` when storage has been provisioned successfully. Persistent storage helps retain database files when a pod is replaced, but deleting the PVC or its underlying volume may still result in data loss.

## 11. Resource Requests and Limits

The Flask and MongoDB containers use the following configured resource values:

| Workload | CPU Request | Memory Request | CPU Limit | Memory Limit |
|---|---:|---:|---:|---:|
| Flask | 200m | 250Mi | 500m | 500Mi |
| MongoDB | 200m | 250Mi | 500m | 500Mi |

- **Requests** tell Kubernetes how much CPU and memory to consider when scheduling a pod.
- **Limits** cap container resource usage. CPU can be throttled at its limit; exceeding a memory limit can cause a container to be terminated.

Inspect resource usage:

```bash
kubectl top pods
kubectl top nodes
```

These are demonstration values and should be tuned for the workload in a production environment.

## 12. Horizontal Pod Autoscaling

The Flask HPA is named `flask-hpa` and is configured for:

- Minimum replicas: `2`
- Maximum replicas: `5`
- Target CPU utilization: `70%`

Inspect it:

```bash
kubectl get hpa
kubectl describe hpa flask-hpa
```

The Metrics Server must be available, and the Flask containers must have CPU resource requests for CPU utilization-based scaling.

### Load Test

With the port-forward command running, use a separate terminal to generate concurrent requests:

```bash
for i in $(seq 1 1000); do
  curl -s http://localhost:8080/ > /dev/null &
done
wait
```

Monitor HPA and pod counts:

```bash
kubectl get hpa flask-hpa --watch
```

In another terminal:

```bash
kubectl get pods --watch
```

A short or low-CPU workload may not cause scaling. During the recorded test, HPA metrics were available and CPU utilization was approximately `4–6%` against the `70%` target; the replica count remained at `2`. Therefore, autoscaling was configured and monitored, but an increase in replicas was not observed in that test. Do not report that scaling occurred unless a later test actually shows more than two replicas.

## 13. Testing Summary

The following checks were performed in the Minikube environment:

- Minikube node reported `Ready`.
- MongoDB StatefulSet pod `mongodb-0` was running.
- MongoDB PVC `mongodb-pvc` was `Bound` with `1Gi` requested storage.
- Flask Deployment ran two replicas.
- Flask Service was accessible using port forwarding.
- POST `/data` returned `201 Created`.
- GET `/data` returned the inserted JSON document.
- Metrics Server data was available through `kubectl top`.
- HPA showed CPU metrics, but the tested workload did not increase the replica count beyond two.

Use screenshots of the actual command output and application responses as evidence for these results.

## 14. Design Choices

### Flask
Flask is lightweight and suitable for this small REST API. Django or FastAPI could be alternatives, but their additional features were not required for this demonstration.

### MongoDB
MongoDB stores flexible JSON-like documents, which suit the `/data` endpoint. PostgreSQL or MySQL would be alternatives if relational data and SQL constraints were needed.

### Docker
Docker packages the application and its dependencies into an image, making the application easier to run consistently.

### Minikube
Minikube provides a local Kubernetes cluster for development and demonstration. A managed Kubernetes service is a possible choice for production.

### StatefulSet and Persistent Storage
A StatefulSet provides stable pod identity and works with persistent storage for MongoDB. Production databases also need backup, recovery, security, monitoring, and an appropriate replication strategy.

### Services
The MongoDB ClusterIP Service provides internal cluster access. The Flask Service exposes the application within the cluster and can be accessed locally with `kubectl port-forward`.

### HPA
CPU-based HPA is a straightforward demonstration of scaling Flask replicas. It depends on metrics and available cluster capacity. Production deployments may also require request-rate or latency-based metrics.

## 15. Troubleshooting

### Pods are not starting

```bash
kubectl get pods
kubectl describe pod POD_NAME
kubectl logs POD_NAME
```

Replace `POD_NAME` with the actual pod name.

### MongoDB connection errors

```bash
kubectl get pods
kubectl get service mongodb
kubectl logs mongodb-0
```

Verify the Secret keys, username, password, URL encoding, and connection URI.

### HPA metrics are unavailable

```bash
kubectl get pods -n kube-system
kubectl top pods
kubectl describe hpa flask-hpa
```

Confirm that the Metrics Server is ready and that CPU requests are configured.

### Application is not accessible

```bash
kubectl get service flask-service
kubectl port-forward service/flask-service 8080:5000
```

Keep port forwarding running and browse to `http://localhost:8080/`.

## 16. Cleanup

Delete resources applied from the manifest:

```bash
kubectl delete -f k8s/app.yaml
```

If the Secret was created separately, delete it when it is no longer needed:

```bash
kubectl delete secret mongodb-secret
```

Stop Minikube:

```bash
minikube stop
```

Check persistent volumes and PVCs before deleting storage, because cleanup behavior depends on the configured storage provider and reclaim policy.

## 17. Conclusion

This project demonstrates containerizing a Flask API, deploying Flask and MongoDB on Kubernetes with Minikube, using Kubernetes Services and DNS for communication, persisting MongoDB data, setting CPU and memory requests and limits, and configuring and testing HPA.

The results documented above reflect the observed test: the application and database interactions worked, HPA metrics were available, and the replica count remained at two during the recorded load test.
# flask-mongodb-app-faralpha
