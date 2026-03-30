import os
from nimbus.generators.cicd import generate_github_actions

def generate_infrastructure(project, architecture, output_dir, env="dev"):
    os.makedirs(output_dir, exist_ok=True)

    from nimbus.generators.terraform import generate_terraform
    tf_dir = os.path.join(output_dir, "terraform")
    generate_terraform(project, architecture, tf_dir, env)

    if architecture in ["microservices", "event_driven", "django_async"]:
        from nimbus.generators.kubernetes import generate_kubernetes
        k8s_dir = os.path.join(output_dir, "k8s")
        generate_kubernetes(project, architecture, k8s_dir)

    generate_github_actions(project, architecture, output_dir, env)

    return output_dir