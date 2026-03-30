import os


def generate_github_actions(project, architecture, output_dir, env):
    workflows_dir = os.path.join(output_dir, ".github", "workflows")
    os.makedirs(workflows_dir, exist_ok=True)

    workflow = f"""
name: Nimbus Deploy ({env})

on:
  push:
    branches:
      - main

env:
  ENV: {env}

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

"""

    # -----------------------------
    # Docker build (for container arch)
    # -----------------------------
    if architecture in ["microservices", "event_driven", "django_async"]:
        workflow += """
      - name: Build Docker Image
        run: |
          docker build -t nimbus-app .

      - name: Login to AWS ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Push to ECR
        run: |
          echo "Tag and push image here"
"""

    # -----------------------------
    # Terraform deployment
    # -----------------------------
    workflow += f"""
  terraform:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        run: terraform -chdir=terraform init

      - name: Terraform Apply
        run: terraform -chdir=terraform apply -auto-approve -var-file={env}.tfvars
"""

    # -----------------------------
    # Kubernetes deploy
    # -----------------------------
    if architecture in ["microservices", "event_driven", "django_async"]:
        workflow += """
  deploy:
    runs-on: ubuntu-latest
    needs: terraform

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure kubectl
        run: |
          aws eks update-kubeconfig --region us-west-1 --name nimbus-${{ env.ENV }}-eks

      - name: Deploy to Kubernetes
        run: |
          kubectl apply -f k8s/
"""

    # -----------------------------
    # Serverless deploy
    # -----------------------------
    elif architecture == "serverless":
        workflow += """
  deploy:
    runs-on: ubuntu-latest
    needs: terraform

    steps:
      - name: Deploy Lambda
        run: |
          echo "Deploy Lambda here"
"""

    with open(os.path.join(workflows_dir, "deploy.yml"), "w") as f:
        f.write(workflow.strip())