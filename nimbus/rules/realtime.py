def rule_realtime(engine):
    if engine.project.get("real_time"):
        engine.add_score("event_driven", 7, "Real-time requires event systems")
        engine.add_score("microservices", 5, "WebSocket scalability")