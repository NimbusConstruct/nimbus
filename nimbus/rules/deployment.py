def rule_deployment(engine):
    deployment = engine.project.get("deployment")

    if deployment == "serverless":
        engine.add_score("serverless", 8, "Serverless preference")

    elif deployment == "container":
        engine.add_score("microservices", 4, "Container-based scaling")
        engine.add_score("django_async", 3, "Container-friendly monolith")