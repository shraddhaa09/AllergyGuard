"""
Generate visualization charts for AllergyGuard evaluation and error analysis.

Outputs:
- reports/evaluation_metrics.png
- reports/evidence_status_summary.png
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

REPORTS_DIR = Path("reports")


def generate_metrics_chart():
    allergens = ["WHEAT", "SOY", "MILK"]
    baseline_f1 = [1.0, 1.0, 1.0]
    current_f1 = [1.0, 1.0, 1.0]

    x = np.arange(len(allergens))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)

    rects1 = ax.bar(x - width / 2, baseline_f1, width, label="Baseline", color="#5C6BC0", edgecolor="#3949AB")
    rects2 = ax.bar(x + width / 2, current_f1, width, label="Current Pipeline", color="#26A69A", edgecolor="#00897B")

    ax.set_ylabel("F1 Score", fontsize=12, fontweight="bold")
    ax.set_title("Verified Evaluation Set: Baseline vs Current Pipeline", fontsize=14, fontweight="bold", pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(allergens, fontsize=11, fontweight="bold")
    ax.set_ylim(0, 1.25)

    # Subtitle / Annotation
    plt.suptitle("2 verified images; 3 target allergens (Small Evaluation Set)", fontsize=10, fontstyle="italic", y=0.92)

    ax.legend(loc="upper right", frameon=True, facecolor="#F5F5F5", edgecolor="#CCCCCC")

    # Add values on top of bars
    for rect in rects1:
        height = rect.get_height()
        ax.annotate(f"{height:.2f}",
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha="center", va="bottom", fontsize=10, fontweight="bold", color="#3949AB")

    for rect in rects2:
        height = rect.get_height()
        ax.annotate(f"{height:.2f}",
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha="center", va="bottom", fontsize=10, fontweight="bold", color="#00897B")

    # Disclaimer note box
    disclaimer = (
        "Note: Based on a small verified evaluation set of 2 images.\n"
        "Both baseline and current pipeline produced identical binary decisions."
    )
    ax.text(0.5, 0.05, disclaimer, transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9, fontstyle="italic",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFF9C4", alpha=0.8, edgecolor="#FBC02D"))

    ax.grid(axis="y", linestyle="--", alpha=0.5)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS_DIR / "evaluation_metrics.png"
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path)
    plt.close()
    print(f"Saved metrics chart: {output_path}")


def generate_evidence_status_chart():
    cases = [
        ("CONTAINS: WHEAT, SOY, MILK", "DETECTED", "#2E7D32"),
        ("SOYBEAN OIL", "DETECTED", "#2E7D32"),
        ("Nested MILK", "DETECTED", "#2E7D32"),
        ("SOY LEOTAIN", "POTENTIAL", "#EF6C00"),
        ("ONION SUNFLOWER OIL", "AMBIGUOUS", "#6A1B9A"),
        ("oreo.jpg", "UNCERTAIN", "#616161"),
    ]

    status_levels = {"DETECTED": 4, "POTENTIAL": 3, "AMBIGUOUS": 2, "UNCERTAIN": 1}

    inputs = [c[0] for c in reversed(cases)]
    statuses = [c[1] for c in reversed(cases)]
    colors = [c[2] for c in reversed(cases)]
    x_vals = [status_levels[s] for s in statuses]

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    y_pos = np.arange(len(inputs))
    bars = ax.barh(y_pos, x_vals, color=colors, height=0.55, edgecolor="#333333", alpha=0.9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(inputs, fontsize=10, fontweight="bold")
    ax.set_xticks([1, 2, 3, 4])
    ax.set_xticklabels(["UNCERTAIN", "AMBIGUOUS", "POTENTIAL", "DETECTED"], fontsize=11, fontweight="bold")
    ax.set_xlim(0, 4.8)

    ax.set_title("AllergyGuard Evidence & Uncertainty Examples", fontsize=14, fontweight="bold", pad=20)
    plt.suptitle("Observed Categorical System Statuses Across Error Analysis Cases", fontsize=10, fontstyle="italic", y=0.93)

    # Annotate each bar with status label
    for bar, status, color in zip(bars, statuses, colors):
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height() / 2, status,
                va="center", ha="left", fontsize=10, fontweight="bold", color=color)

    # Note banner
    note = "Categorical decision status based on ingredient evidence and normalization confidence (Not numerical probabilities)."
    ax.text(0.5, 0.02, note, transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9, fontstyle="italic",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#E1F5FE", alpha=0.8, edgecolor="#0288D1"))

    ax.grid(axis="x", linestyle="--", alpha=0.5)

    output_path = REPORTS_DIR / "evidence_status_summary.png"
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path)
    plt.close()
    print(f"Saved evidence status chart: {output_path}")


def main():
    generate_metrics_chart()
    generate_evidence_status_chart()


if __name__ == "__main__":
    main()
