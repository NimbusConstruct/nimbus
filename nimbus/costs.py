def estimate_cost(project, architecture):
    scale = project.get("user_scale", "medium")

    # -------------------------
    # Base compute cost
    # -------------------------
    compute_cost = 0

    if architecture == "django_monolith":
        compute_cost = 20 if scale == "small" else 50 if scale == "medium" else 120

    elif architecture == "django_async":
        compute_cost = 40 if scale == "small" else 90 if scale == "medium" else 180

    elif architecture == "microservices":
        compute_cost = 80 if scale == "small" else 180 if scale == "medium" else 350

    elif architecture == "event_driven":
        compute_cost = 60 if scale == "small" else 150 if scale == "medium" else 300

    elif architecture == "serverless":
        compute_cost = 10 if scale == "small" else 40 if scale == "medium" else 120

    else:
        compute_cost = 50

    # -------------------------
    # Database (RDS)
    # -------------------------
    db_cost = 15 if scale == "small" else 40 if scale == "medium" else 100

    # -------------------------
    # Networking (ALB, data transfer)
    # -------------------------
    network_cost = 10 if scale == "small" else 30 if scale == "medium" else 80

    # -------------------------
    # Real-time adds overhead
    # -------------------------
    if project.get("real_time"):
        compute_cost *= 1.3

    # -------------------------
    # Integrations overhead
    # -------------------------
    integrations = len(project.get("integrations", []))
    compute_cost += integrations * 10

    total = round(compute_cost + db_cost + network_cost, 2)

    return {
        "total": total,
        "breakdown": {
            "compute": round(compute_cost, 2),
            "database": db_cost,
            "network": network_cost
        }
    }