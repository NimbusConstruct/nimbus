def rule_app_type(engine):
    if engine.project["app_type"] in ["static", "brochure"]:
        engine.add_score("static_site", 10, "Static site requirement")
    else:
        engine.add_score("django_monolith", 3, "Dynamic app baseline")
        engine.add_score("microservices", 2, "Scalable dynamic app")
