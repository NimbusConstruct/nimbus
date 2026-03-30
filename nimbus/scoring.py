from collections import defaultdict


class ScoringEngine:

    def __init__(self, project):
        self.project = project
        self.scores = defaultdict(int)
        self.reasons = defaultdict(list)

    def add_score(self, arch, points, reason):
        self.scores[arch] += points
        self.reasons[arch].append(reason)

    def normalize(self):
        total = sum(self.scores.values()) or 1

        return {
            arch: {
                "score": score,
                "confidence": round(score / total, 2),
                "reasons": self.reasons[arch],
            }
            for arch, score in self.scores.items()
        }