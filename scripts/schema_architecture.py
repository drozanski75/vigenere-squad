"""Dessine docs/architecture.png (figure du rapport)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ENCRE, ENCRE2, BLEU, ORANGE, VERT, FOND = "#2b2b2a", "#6b6a63", "#2a78d6", "#eb6834", "#1baf7a", "#f3f1ec"


def boite(ax, x, y, w, h, titre, sous="", couleur=BLEU):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc="white", ec=couleur, lw=1.6))
    ax.text(x + w / 2, y + h * 0.66, titre, ha="center", va="center", fontsize=9.5, color=ENCRE, weight="bold")
    if sous:
        ax.text(x + w / 2, y + h * 0.3, sous, ha="center", va="center", fontsize=7, color=ENCRE2)


def fleche(ax, a, b, texte="", couleur=ENCRE2, courbe=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, color=couleur, lw=1.2,
                                 connectionstyle=f"arc3,rad={courbe}"))
    if texte:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.12, texte, ha="center", fontsize=7, color=couleur)


fig, ax = plt.subplots(figsize=(10, 5.2))
ax.set_xlim(0, 10)
ax.set_ylim(0, 5.2)
ax.axis("off")
ax.add_patch(FancyBboxPatch((0.2, 4.05), 9.6, 0.8, boxstyle="round,pad=0.02,rounding_size=0.1", fc=FOND, ec=ENCRE2))
ax.text(5, 4.6, "Orchestrateur", ha="center", fontsize=11, weight="bold", color=ENCRE)
ax.text(5, 4.25, "état partagé typé · réessais · replis déterministes · garde-fou · journal JSONL",
        ha="center", fontsize=8, color=ENCRE2)
agents = [("Classifieur", "IC, fréquences"), ("Cryptanalyste", "Kasiski, Friedman, χ²,\naffine, recuit, autoclave"),
          ("Linguiste", "score quadrigrammes"), ("Pédagogue", "aucun outil\n(lit les traces)"),
          ("Vérificateur", "chiffrer / casser\nl'exercice")]
xs = [0.3, 2.25, 4.2, 6.15, 8.1]
for (n, s), x in zip(agents, xs):
    boite(ax, x, 2.45, 1.6, 1.05, n, s)
    fleche(ax, (x + 0.8, 4.05), (x + 0.8, 3.52))
fleche(ax, (3.87, 2.98), (4.2, 2.98), "", ENCRE2)
fleche(ax, (4.55, 2.43), (3.5, 2.43), "", ORANGE, courbe=-0.9)
ax.text(4.02, 1.86, "non plausible : nouvelle hypothèse (≤ 6)", ha="center", fontsize=7, color=ORANGE,
        bbox=dict(fc="white", ec="none", pad=1))
fleche(ax, (7.75, 2.98), (8.1, 2.98))
ax.add_patch(FancyBboxPatch((0.2, 0.55), 9.6, 1.1, boxstyle="round,pad=0.02,rounding_size=0.1", fc="white",
                            ec=VERT, lw=1.6))
ax.text(5, 1.3, "Outils déterministes (Python, testés, couverture ≥ 70 %)", ha="center", fontsize=10,
        weight="bold", color=ENCRE)
ax.text(5, 0.88, "toute la cryptographie et tous les calculs — jamais le modèle de langage · "
        "liste fermée par agent · arguments validés", ha="center", fontsize=8, color=ENCRE2)
for x in xs:
    if x not in (6.15,):
        fleche(ax, (x + 0.8, 2.43), (x + 0.8, 1.68), couleur=VERT)
ax.text(5, 0.15, "Modèle local (Ollama, Qwen3) partagé par les agents : il décide et explique ; le code calcule.",
        ha="center", fontsize=8, color=ENCRE2, style="italic")
sortie = Path(__file__).resolve().parents[1] / "docs" / "architecture.png"
fig.savefig(sortie, dpi=160, bbox_inches="tight", metadata={"Software": None})
print(sortie)
