def rule_integrations(engine):
    integrations = engine.project.get("integrations", [])

    if not integrations:
        return

    if any(i in integrations for i in ["slack", "github"]):
        engine.add_score("django_async", 4, "Webhook-heavy integrations")
        engine.add_score("event_driven", 5, "Event-driven integration pattern")

    if "jira" in integrations:
        engine.add_score("django_async", 3, "Polling/background jobs needed")