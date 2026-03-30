from nimbus.explainer import get_explanation


def get_top_architectures(results, top_n=3):
    sorted_arch = sorted(
        results.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )
    return sorted_arch[:top_n]


def compare_architectures(results):
    top = get_top_architectures(results)

    output = []
    output.append("\n🏆 Top Architecture Options\n")

    # Ranking
    for i, (arch, data) in enumerate(top, start=1):
        output.append(f"{i}. {arch} ({data['confidence']})")

    output.append("\n----------------------------------------\n")
    output.append("🔍 Comparison\n")

    # Side-by-side comparison
    for arch, data in top:
        explanation = get_explanation(arch)

        output.append(f"[{arch}]")

        for w in explanation["why"][:2]:
            output.append(f"+ {w}")

        for t in explanation["tradeoffs"][:2]:
            output.append(f"- {t}")

        output.append("")

    # Why #1 wins
    if len(top) > 1:
        winner, win_data = top[0]
        runner_up, runner_data = top[1]

        output.append("----------------------------------------\n")
        output.append(f"⚖️ Why {winner} Wins\n")

        win_reasons = set(win_data["reasons"])
        runner_reasons = set(runner_data["reasons"])

        diff = win_reasons - runner_reasons

        if diff:
            for d in list(diff)[:3]:
                output.append(f"- {d}")
        else:
            output.append("- Higher overall score based on combined factors")

    return "\n".join(output)