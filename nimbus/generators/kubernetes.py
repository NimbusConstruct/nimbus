import os


def generate_kubernetes(project, architecture, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    deployment = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nimbus-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nimbus
  template:
    metadata:
      labels:
        app: nimbus
    spec:
      containers:
      - name: app
        image: nimbus:latest
        ports:
        - containerPort: 8000
"""

    service = """
apiVersion: v1
kind: Service
metadata:
  name: nimbus-service
spec:
  selector:
    app: nimbus
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
"""

    with open(os.path.join(output_dir, "deployment.yaml"), "w") as f:
        f.write(deployment.strip())

    with open(os.path.join(output_dir, "service.yaml"), "w") as f:
        f.write(service.strip())