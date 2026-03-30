# nimbus

🌩️ Nimbus

Nimbus is a modular, cloud-integrated platform designed to streamline application provisioning, infrastructure orchestration, and secure API-driven workflows. It combines a CLI tool, REST API, and intelligent rules engine to help developers and teams rapidly build, configure, and deploy modern applications.

🚀 Features

⚙️ CLI Tooling

- Global command access via nimbus
- Built with argparse for flexibility and extensibility
- Config initialization and environment setup

☁️ Cloud Integration

- AWS (initial support)
- Extensible to other providers (Linode, GCP, Azure)
- Secure API key management

🔐 Security First

- JWT authentication (with expiration + refresh tokens)
- Optional mTLS support
- Role-based access (admin/user)
- Token revocation (logout support)

🧠 Rules Engine (v2)

- Intelligent decision-making for infrastructure workflows
- Pluggable logic system
- Future AI-enhanced recommendations

🌐 Django REST API

- Async-ready endpoints
- Rate-limited (40 req/sec target)
- Designed for external integrations

📦 Containerized Deployment

- Podman/Docker support
- Kubernetes-ready architecture

### Clone the Repository

```bash
git clone https://github.com/yourusername/nimbus.git
cd nimbus
```

### Setup the Environment

```bash
pip install pipenv
pipenv install
pipenv shell
```

### Initialize Configuration

```bash
nimbus --config init
```

### Initialize with Cloud Provider

```bash
nimbus --config init --cloud aws --apikey YOUR_API_KEY
```

### Configuration

Nimbus stores configuration in a local file (e.g, `.nimbus/config.yaml`)

```yaml
cloud: aws
api_key: YOUR_API_KEY
environment: dev
```

### Authentication Model

- JWT-based authentication
- Access + refresh tokens
- Role-based permissions:
  - admin
  - user

Future enhancements:
    - mTLS enforcement
    - key rotation automation

### Rules Engine Overview

Nimbus uses a pluggable rules engine to determine:
    - Infrastructure setup decisions
    - Security enforcement
    - Deployment strategies

Future version (v2):
    - AI-assisted decision making
    - Dynamic rule evaluation
    - Policy-driven architecture

☸️ Kubernetes (Planned)

- Deployment manifests
- Horizontal scaling
- Secure secret management

🧪 Testing

- pytest

🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Commit changes
4. Submit a pull request

💡 Vision

Nimbus aims to be a developer-first platform that unifies CLI tooling, API automation, and intelligent infrastructure decisions into a single ecosystem.