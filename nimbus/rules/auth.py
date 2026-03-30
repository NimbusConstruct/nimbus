def rule_auth(engine):
    if engine.project.get("auth_required"):
        engine.add_score("django_monolith", 3, "Auth fits Django well")
        engine.add_score("django_async", 2, "Async auth support")
    else:
        engine.add_score("static_site", 5, "No auth simplifies stack")