from nimbus.scoring import ScoringEngine

from nimbus.rules.app_type import rule_app_type
from nimbus.rules.auth import rule_auth
from nimbus.rules.scale import rule_scale
from nimbus.rules.integrations import rule_integrations
from nimbus.rules.realtime import rule_realtime
from nimbus.rules.security import rule_security
from nimbus.rules.deployment import rule_deployment


RULES = [
    rule_app_type,
    rule_auth,
    rule_scale,
    rule_integrations,
    rule_realtime,
    rule_security,
    rule_deployment,
]


class SmartArchitectureEngine:

    def __init__(self, project: dict):
        self.project = project

    def analyze(self):
        engine = ScoringEngine(self.project)

        for rule in RULES:
            rule(engine)

        results = engine.normalize()

        best = max(results.items(), key=lambda x: x[1]["score"])

        return {
            "recommended": best[0],
            "details": results,
            "explanation": best[1]["reasons"],
        }