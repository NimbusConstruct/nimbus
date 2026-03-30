def rule_scale(engine):
    scale = engine.project.get("user_scale")

    if scale == "low":
        engine.add_score("django_monolith", 5, "Low scale favors simplicity")

    elif scale == "medium":
        engine.add_score("django_async", 4, "Moderate scale needs async")

    elif scale == "high":
        engine.add_score("microservices", 6, "High scale needs distribution")
        engine.add_score("event_driven", 8, "Event-driven scaling advantage")