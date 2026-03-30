def rule_security(engine):
    if engine.project.get("sensitive_data"):
        engine.add_score("django_monolith", 3, "Centralized security control")
        engine.add_score("microservices", 2, "Advanced security patterns")

    if engine.project.get("compliance"):
        engine.add_score("microservices", 4, "Service isolation for compliance")
        engine.add_score("event_driven", 3, "Audit-friendly event logs")