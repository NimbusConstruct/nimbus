EXPLANATIONS = {
    "django_monolith": {
        "why": [
            "Simple and fast to develop",
            "Centralized logic makes it easier to maintain",
            "Great fit for low to medium scale apps"
        ],
        "tradeoffs": [
            "Harder to scale at very high loads",
            "Tight coupling of components",
            "Limited flexibility for independent services"
        ],
        "avoid_when": [
            "You expect massive scale",
            "You need independent service deployments",
            "Complex real-time systems are required"
        ]
    },
    "django_async": {
        "why": [
            "Supports background processing (Celery)",
            "Handles integrations and async workflows well",
            "Good balance of simplicity and scalability"
        ],
        "tradeoffs": [
            "More moving parts (Redis, workers)",
            "Slightly more complex deployment",
            "Debugging async tasks can be harder"
        ],
        "avoid_when": [
            "No background jobs are needed",
            "Very small/simple apps",
            "Strict low-latency real-time systems"
        ]
    },
    "microservices": {
        "why": [
            "Enables independent scaling of components",
            "Better for large teams and complex systems",
            "Improves fault isolation"
        ],
        "tradeoffs": [
            "High operational complexity",
            "Requires orchestration (Kubernetes)",
            "Harder debugging across services"
        ],
        "avoid_when": [
            "Small teams",
            "Simple applications",
            "Tight deadlines (MVPs)"
        ]
    },
    "event_driven": {
        "why": [
            "Excellent for real-time and high-scale systems",
            "Handles integrations via events/webhooks",
            "Highly scalable and decoupled"
        ],
        "tradeoffs": [
            "Complex architecture",
            "Requires message brokers (Kafka/SQS)",
            "Eventual consistency challenges"
        ],
        "avoid_when": [
            "Simple CRUD apps",
            "Low traffic systems",
            "Teams unfamiliar with event systems"
        ]
    },
    "serverless": {
        "why": [
            "No infrastructure management",
            "Scales automatically",
            "Cost-efficient for low/variable workloads"
        ],
        "tradeoffs": [
            "Cold starts",
            "Vendor lock-in",
            "Limited long-running tasks"
        ],
        "avoid_when": [
            "High-performance low-latency apps",
            "Long-running processes",
            "Complex stateful systems"
        ]
    },
    "static_site": {
        "why": [
            "Fast and cheap to host",
            "Minimal maintenance",
            "Highly scalable via CDN"
        ],
        "tradeoffs": [
            "No backend logic",
            "Limited interactivity",
            "Requires separate APIs for dynamic features"
        ],
        "avoid_when": [
            "User authentication is required",
            "Dynamic data processing is needed"
        ]
    }
}


def get_explanation(arch):
    return EXPLANATIONS.get(arch, {
        "why": ["No explanation available"],
        "tradeoffs": [],
        "avoid_when": []
    })