import os


def generate_terraform(project, architecture, output_dir, env):
    os.makedirs(output_dir, exist_ok=True)

    # -------------------------
    # variables.tf
    # -------------------------
    variables_tf = """
variable "env" {
  type = string
}

variable "db_username" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}
"""

    with open(os.path.join(output_dir, "variables.tf"), "w") as f:
        f.write(variables_tf.strip())

    # -------------------------
    # main.tf
    # -------------------------
    main_tf = f"""
provider "aws" {{
  region = "us-west-1"
}}

locals {{
  env = var.env
}}

# -------------------------
# Secrets Manager
# -------------------------
resource "aws_secretsmanager_secret" "db_secret" {{
  name = "nimbus/${{local.env}}/db"
}}

resource "aws_secretsmanager_secret_version" "db_secret_value" {{
  secret_id = aws_secretsmanager_secret.db_secret.id

  secret_string = jsonencode({{
    username = var.db_username
    password = var.db_password
  }})
}}

# -------------------------
# VPC (env scoped)
# -------------------------
resource "aws_vpc" "main" {{
  cidr_block = "10.0.0.0/16"

  tags = {{
    Name = "nimbus-${{local.env}}-vpc"
  }}
}}

# -------------------------
# RDS
# -------------------------
resource "aws_db_instance" "postgres" {{
  identifier = "nimbus-${{local.env}}-db"

  engine            = "postgres"
  instance_class    = "db.t3.micro"
  allocated_storage = 20

  db_name  = "nimbus"

  username = var.db_username
  password = var.db_password

  skip_final_snapshot = true
}}
"""

    if architecture in ["microservices", "event_driven", "django_async"]:
        main_tf += """
# -------------------------
# EKS Cluster
# -------------------------
resource "aws_eks_cluster" "main" {
  name     = "nimbus-${local.env}-eks"
  role_arn = "REPLACE_ME"
}
"""

    with open(os.path.join(output_dir, "main.tf"), "w") as f:
        f.write(main_tf.strip())

    # -------------------------
    # tfvars per environment
    # -------------------------
    env_configs = {
        "dev": {
            "db_username": "devuser",
            "db_password": "devpass123"
        },
        "staging": {
            "db_username": "stageuser",
            "db_password": "stagepass123"
        },
        "prod": {
            "db_username": "produser",
            "db_password": "CHANGE_ME_SECURE"
        }
    }

    for env_name, vals in env_configs.items():
        tfvars = f"""
env = "{env_name}"
db_username = "{vals['db_username']}"
db_password = "{vals['db_password']}"
"""
        with open(os.path.join(output_dir, f"{env_name}.tfvars"), "w") as f:
            f.write(tfvars.strip())