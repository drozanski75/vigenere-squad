"""Figures régénérées à partir de results/metrics.json (matplotlib, sans état)."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .executer import RESULTS  # noqa: E402
from .metriques import ORDRE_TRANCHES, PROCEDES  # noqa: E402

# Palette catégorielle validée (3 premiers créneaux : valides en toutes paires)
COULEURS = ["#2a78d6", "#eb6834", "#1baf7a"]
MARQUEURS = ["o", "s", "^"]
ENCRE, ENCRE_2, GRILLE = "#2b2b2a", "#6b6a63", "#e4e2dc"

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": ENCRE_2, "axes.labelcolor": ENCRE, "xtick.color": ENCRE_2,
    "ytick.color": ENCRE_2, "axes.grid": True, "grid.color": GRILLE, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2, "lines.markersize": 5,
    "legend.frameon": False, "figure.dpi": 130, "axes.axisbelow": True,
})


def _sauver(fig, nom: str) -> str:
    d = RESULTS / "figures"
    d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / f"{nom}.png", bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    return f"figures/{nom}.png"


def fig_taux_par_longueur(m: dict, experience: str = "principal") -> str | None:
    exp = m["experiences"].get(experience)
    if not exp:
        return None
    configs = sorted(exp)
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.6), sharex=True, sharey=True)
    for ax, p in zip(axes.flat, PROCEDES):
        for i, c in enumerate(configs):
            pt = exp[c]["par_procede_tranche"].get(p, {})
            xs = [k for k, t in enumerate(ORDRE_TRANCHES) if t in pt]
            ys = [pt[ORDRE_TRANCHES[k]]["moyenne"] for k in xs]
            err = [pt[ORDRE_TRANCHES[k]]["ecart_type"] for k in xs]
            ax.errorbar(xs, ys, yerr=err, color=COULEURS[i % 3], marker=MARQUEURS[i % 3], capsize=2, label=c)
        ax.set_title(p, color=ENCRE)
        ax.set_ylim(-5, 105)
        ax.set_xticks(range(len(ORDRE_TRANCHES)), ORDRE_TRANCHES, rotation=40, ha="right")
    for ax in axes[:, 0]:
        ax.set_ylabel("clair exact (%)")
    for ax in axes[1, :]:
        ax.set_xlabel("longueur du texte (lettres)")
    axes[0, 0].legend(loc="lower right")
    fig.suptitle(f"Taux de clair exact par procédé et longueur ({experience}), moyenne ± écart type",
                 color=ENCRE)
    return _sauver(fig, f"taux_par_longueur_{experience}")


def fig_shannon(m: dict) -> str | None:
    s = m.get("shannon", {}).get("par_longueur_cle")
    if not s:
        return None
    Ls = sorted(int(k) for k in s)
    fig, ax = plt.subplots(figsize=(6.4, 4))
    y = [s[str(L)]["longueur_min_90"] for L in Ls]
    yo = [s[str(L)]["longueur_min_90_longueur_connue"] for L in Ls]
    ue = [s[str(L)]["distance_unicite_estimee"] for L in Ls]
    ul = [s[str(L)]["distance_unicite_litterature"] for L in Ls]
    ax.plot(Ls, y, color=COULEURS[0], marker="o", label="mesurée : longueur inconnue (Kasiski+Friedman)")
    ax.plot(Ls, yo, color=COULEURS[1], marker="s", label="mesurée : longueur de clé connue")
    ax.plot(Ls, ue, color=ENCRE_2, linestyle="--", linewidth=1.5,
            label=f"distance d'unicité, D estimée = {m['shannon']['redondance_estimee_bits']} bits")
    ax.plot(Ls, ul, color=ENCRE_2, linestyle=":", linewidth=1.5,
            label=f"distance d'unicité, D = {m['shannon']['redondance_litterature_bits']} bits")
    ax.set_xlabel("longueur de la clé (lettres)")
    ax.set_ylabel("longueur de texte (lettres)")
    ax.set_title("Vigenère : longueur minimale pour 90 % de succès vs distance d'unicité", color=ENCRE, fontsize=9)
    ax.legend(fontsize=7.5)
    return _sauver(fig, "shannon")


def fig_ablation(m: dict) -> str | None:
    exp = m["experiences"].get("principal")
    if not exp:
        return None
    configs = sorted(exp)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4))
    for i, c in enumerate(configs):
        v = exp[c]
        ref = v.get("comparaison_reference", {}).get("reference_sur_sous_ensemble")
        a1.bar(i, v["taux_exact"]["moyenne"], yerr=v["taux_exact"]["ecart_type"], color=COULEURS[i % 3],
               width=0.6, capsize=3)
        a1.text(i, v["taux_exact"]["moyenne"] + 3, f"{v['taux_exact']['moyenne']:.1f}", ha="center", color=ENCRE)
        if ref:
            a1.plot([i - 0.3, i + 0.3], [ref["moyenne"]] * 2, color=ENCRE, linewidth=1.2, linestyle="--")
        a2.bar(i, v["duree_moyenne_s"]["moyenne"], yerr=v["duree_moyenne_s"]["ecart_type"],
               color=COULEURS[i % 3], width=0.6, capsize=3)
    for a in (a1, a2):
        a.set_xticks(range(len(configs)), configs, rotation=15)
    a1.set_ylabel("clair exact (%)")
    a1.set_ylim(0, 110)
    a1.set_title("Taux de clair exact (tirets : référence (a) sur le même sous-ensemble)", fontsize=8, color=ENCRE)
    a2.set_ylabel("durée moyenne par chiffré (s)")
    a2.set_title("Coût en temps", fontsize=8, color=ENCRE)
    return _sauver(fig, "ablation")


def fig_robustesse(m: dict) -> str | None:
    exps = ["principal"] + sorted(k for k in m["experiences"] if k.startswith("robustesse"))
    exps = [e for e in exps if e in m["experiences"]]
    if len(exps) < 2:
        return None
    configs = sorted({c for e in exps for c in m["experiences"][e]})
    fig, ax = plt.subplots(figsize=(8, 3.4))
    w = 0.8 / len(configs)
    for i, c in enumerate(configs):
        xs, ys, es = [], [], []
        for k, e in enumerate(exps):
            v = m["experiences"][e].get(c)
            if v:
                xs.append(k + i * w)
                ys.append(v["taux_exact"]["moyenne"])
                es.append(v["taux_exact"]["ecart_type"])
        ax.bar(xs, ys, width=w * 0.92, yerr=es, color=COULEURS[i % 3], label=c, capsize=2)
    ax.set_xticks([k + w * (len(configs) - 1) / 2 for k in range(len(exps))],
                  [e.replace("robustesse_", "") for e in exps], rotation=15)
    ax.set_ylabel("clair exact (%)")
    ax.set_ylim(0, 105)
    ax.legend(fontsize=8)
    ax.set_title("Robustesse : sans espaces, 5 % de fautes, corpus anglais", color=ENCRE)
    return _sauver(fig, "robustesse")


def fig_kasiski(m: dict) -> str | None:
    k = m.get("kasiski_autoclave")
    if not k:
        return None
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    labels = ["Kasiski : bonne longueur en tête", "Kasiski : bonne longueur dans le top 3"]
    for i, p in enumerate(("vigenere", "autoclave")):
        vals = [k[p]["kasiski_tete_correcte_pct"], k[p]["kasiski_top3_pct"]]
        ax.bar([x + i * 0.38 for x in range(2)], vals, width=0.35, color=COULEURS[i], label=p)
        for x, v in enumerate(vals):
            ax.text(x + i * 0.38, v + 2, f"{v:.0f}", ha="center", color=ENCRE, fontsize=8)
    ax.set_xticks([0.19, 1.19], labels)
    ax.set_ylabel("% des chiffrés")
    ax.set_ylim(0, 110)
    ax.legend()
    ax.set_title("Pourquoi Kasiski échoue sur l'autoclave", color=ENCRE)
    return _sauver(fig, "kasiski_autoclave")


def generer_figures() -> list[str]:
    m = json.loads((RESULTS / "metrics.json").read_text(encoding="utf-8"))
    sorties = [fig_taux_par_longueur(m), fig_shannon(m), fig_ablation(m), fig_robustesse(m), fig_kasiski(m)]
    for e in m["experiences"]:
        if e.startswith("robustesse") or e == "defaillances":
            sorties.append(fig_taux_par_longueur(m, e))
    return [s for s in sorties if s]
