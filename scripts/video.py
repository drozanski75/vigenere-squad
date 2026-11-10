"""Vidéo de démonstration (sous-titrée) générée à partir des journaux réels de
docs/video/journaux/ et, s'il existe, de results/metrics.json.

Usage : python scripts/video.py [sortie.mp4]
Chaque scène est encodée séparément (H.264, 1280x720, 30 i/s) puis concaténée.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

R = Path(__file__).resolve().parents[1]
J = R / "docs" / "video" / "journaux"
W, H = 1280, 720
F = "/usr/share/fonts/truetype/dejavu/"
POL = {k: ImageFont.truetype(F + v, s) for k, (v, s) in {
    "titre": ("DejaVuSans-Bold.ttf", 54), "sous": ("DejaVuSans.ttf", 26), "h": ("DejaVuSans-Bold.ttf", 26),
    "txt": ("DejaVuSans.ttf", 23), "petit": ("DejaVuSans.ttf", 17), "cap": ("DejaVuSans.ttf", 21),
    "capb": ("DejaVuSans-Bold.ttf", 21), "mono": ("DejaVuSansMono.ttf", 15), "monob": ("DejaVuSansMono-Bold.ttf", 15),
    "gros": ("DejaVuSans-Bold.ttf", 64), "mono18": ("DejaVuSansMono.ttf", 18)}.items()}
FOND, ENCRE, ENCRE2, BLEU, VERT, ORANGE, ROUGE = "#fbfaf7", "#1d1d1b", "#5e5d57", "#2a78d6", "#1baf7a", "#eb6834", "#c62828"
TERM, TTXT = "#101317", "#d8dee6"
SOURCE = "Rejeu de sorties réelles enregistrées sur le PC de l'auteur (Windows 11, qwen3:4b), 10/11/2026"


def base(titre: str | None = None, sombre: bool = False) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGB", (W, H), TERM if sombre else FOND)
    d = ImageDraw.Draw(im)
    if titre:
        d.rectangle([0, 0, W, 58], fill="#1f3556")
        d.text((28, 13), titre, font=POL["h"], fill="white")
        d.text((W - 28, 20), "Vigenère-Squad", font=POL["petit"], fill="#b9c7dc", anchor="ra")
    return im, d


def legende(d: ImageDraw.ImageDraw, texte: str, couleur: str = BLEU) -> None:
    if not texte:
        return
    d.rectangle([0, H - 92, W, H], fill="#ffffff")
    d.rectangle([0, H - 92, 8, H], fill=couleur)
    lignes = textwrap.wrap(texte, 98)[:3]
    y = H - 92 + (92 - 27 * len(lignes)) // 2
    for l in lignes:
        d.text((30, y), l, font=POL["cap"], fill=ENCRE)
        y += 27


def terminal(lignes: list[str], titre: str, cap: str = "", couleur_cap: str = BLEU, chrono: str = "") -> Image.Image:
    im, d = base(titre, sombre=True)
    zone_bas = H - 100
    hauteur = 19
    capacite = (zone_bas - 72) // hauteur
    rendues: list[tuple[str, str]] = []
    for l in lignes:
        coul = TTXT
        if "!!" in l or "ERREUR" in l or "[ATTENTION]" in l:
            coul = "#ffb4a2"
        elif "[ OK ]" in l or "corrige_verifie\": true" in l or "\"plausible\": true" in l and "garde" not in l:
            coul = "#9be7c4"
        elif re.search(r"\] (classifieur|cryptanalyste|linguiste|pedagogue|verificateur)\s+->", l):
            coul = "#9ec9ff"
        elif "** " in l:
            coul = "#f2d38a"
        for i, morceau in enumerate(textwrap.wrap(l, 132, drop_whitespace=False) or [""]):
            if i < 2:
                rendues.append((morceau if i == 0 else "    " + morceau, coul))
    for i, (t, c) in enumerate(rendues[-capacite:]):
        d.text((26, 72 + i * hauteur), t, font=POL["mono"], fill=c)
    if chrono:
        d.text((W - 26, 72), chrono, font=POL["monob"], fill="#f2d38a", anchor="ra")
    legende(d, cap, couleur_cap)
    return im


def diapo(titre: str, puces: list[str], note: str = "", couleur: str = BLEU, cap: str = "") -> Image.Image:
    im, d = base(titre)
    y = 100
    for p in puces:
        for i, l in enumerate(textwrap.wrap(p, 82)):
            if i == 0:
                d.ellipse([46, y + 9, 56, y + 19], fill=couleur)
            d.text((74, y), l, font=POL["txt"], fill=ENCRE)
            y += 32
        y += 12
    if note:
        d.text((46, H - 135 if cap else H - 60), note, font=POL["petit"], fill=ENCRE2)
    legende(d, cap, couleur)
    return im


def ecran_titre() -> Image.Image:
    im, d = base()
    d.rectangle([0, 0, W, 12], fill=BLEU)
    d.text((W // 2, 210), "Vigenère-Squad", font=POL["titre"], fill=ENCRE, anchor="mm")
    d.text((W // 2, 280), "Une équipe d'agents IA qui casse les chiffrements classiques", font=POL["sous"],
           fill=ENCRE2, anchor="mm")
    d.text((W // 2, 316), "et explique sa démarche", font=POL["sous"], fill=ENCRE2, anchor="mm")
    d.text((W // 2, 392), "Le modèle de langage décide et explique ; le code calcule.", font=POL["h"],
           fill=BLEU, anchor="mm")
    d.text((W // 2, 488), "Dawid Rozanski — M1 Cybersécurité, SUP DE VINCI", font=POL["txt"], fill=ENCRE, anchor="mm")
    d.text((W // 2, 524), "Cryptographie appliquée et IA agentique — sujet n° 1", font=POL["petit"], fill=ENCRE2,
           anchor="mm")
    d.text((W // 2, 650), "github.com/drozanski75/vigenere-squad", font=POL["mono18"], fill=ENCRE2, anchor="mm")
    d.text((W // 2, 684), SOURCE, font=POL["petit"], fill=ENCRE2, anchor="mm")
    return im


def image_figure(chemin: Path, titre: str, cap: str) -> Image.Image:
    im, d = base(titre)
    fig = Image.open(chemin).convert("RGB")
    fig.thumbnail((W - 80, H - 58 - 92 - 30))
    im.paste(fig, ((W - fig.width) // 2, 58 + (H - 58 - 92 - fig.height) // 2))
    legende(d, cap)
    return im


def lire(nom: str) -> list[str]:
    return (J / nom).read_text(encoding="utf-8").splitlines()


def horodatage(l: str) -> float | None:
    m = re.match(r"\[\s*([\d.]+)s\]", l.strip())
    return float(m.group(1)) if m else None


# --- Encodage -------------------------------------------------------------------------
def encoder_scene(images: list[tuple[Image.Image, float]], sortie: Path, tmp: Path) -> None:
    dossier = tmp / sortie.stem
    dossier.mkdir()
    liste = []
    for i, (img, duree) in enumerate(images):
        p = dossier / f"{i:04d}.png"
        img.save(p)
        liste.append(f"file '{p}'\nduration {duree:.3f}")
    liste.append(f"file '{dossier / f'{len(images) - 1:04d}.png'}'")
    (dossier / "liste.txt").write_text("\n".join(liste) + "\n")
    provisoire = sortie.with_name(sortie.stem + ".partiel.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(dossier / "liste.txt"),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                    "-r", "30", "-pix_fmt", "yuv420p", str(provisoire)], check=True)
    provisoire.rename(sortie)
    shutil.rmtree(dossier)


def rejeu(lignes: list[str], titre: str, duree_totale: float, legendes: list[tuple[float, str, str]],
          echelle: float | None = None, maintien: float = 6) -> list[tuple[Image.Image, float]]:
    """Fait apparaître les lignes selon leurs horodatages (sinon régulièrement)."""
    temps = []
    dernier = 0.0
    for i, l in enumerate(lignes):
        h = horodatage(l)
        if h is not None and echelle:
            dernier = h * echelle
        elif not echelle:
            dernier = i * duree_totale / max(1, len(lignes))
        temps.append(dernier)
    images = []
    for i, l in enumerate(lignes):
        t = temps[i]
        suivant = temps[i + 1] if i + 1 < len(lignes) else t + maintien
        cap, coul = "", BLEU
        for debut, texte, c in legendes:
            if t >= debut:
                cap, coul = texte, c
        reel = horodatage(l)
        chrono = f"temps réel : {reel:.0f} s" if reel is not None else ""
        images.append((terminal(lignes[: i + 1], titre, cap, coul, chrono), max(0.12, suivant - t)))
    return images


def scenes() -> list[list[tuple[Image.Image, float]]]:
    s = []
    s.append([(ecran_titre(), 10)])
    s.append([(diapo("Le problème", [
        "Un texte chiffré par un procédé classique : César, affine, Vigenère, autoclave, substitution ou Beaufort.",
        "Il faut identifier le procédé, retrouver la clé et le texte clair, puis expliquer la démarche à un étudiant.",
        "La démarche historique (Kasiski, Friedman, analyse de fréquences) se découpe en rôles : identifier, "
        "attaquer, valider, expliquer.",
        "Idée : confier chaque rôle à un agent, avec un modèle de langage local (Qwen3 via Ollama, sans GPU dédié ni "
        "abonnement) qui décide et explique, et du code testé qui fait tous les calculs.",
    ], cap="Aucune opération cryptographique n'est confiée au modèle : le clair annoncé vient toujours d'un outil."),
        20)])
    s.append([(image_figure(R / "docs" / "architecture.png", "Architecture : 5 agents, liste fermée d'outils",
                            "Orchestrateur explicite, boucle Cryptanalyste ⇄ Linguiste, garde-fous déterministes, "
                            "journal JSONL de chaque message et appel d'outil."), 24)])
    s.append(rejeu(lire("installation.txt"), "Installation sous Windows : un double-clic sur installer.bat", 30, [
        (0, "installer.bat installe uv, Ollama et Git (sans PowerShell), démarre Ollama et vérifie l'installation.", BLEU),
        (18, "Les trois modèles sont téléchargés et leurs empreintes (digest) inscrites dans la configuration.", VERT)],
        maintien=10))
    diag = lire("diagnostic.txt")
    s.append(rejeu(diag, "Diagnostic : vsquad diagnostic", 18, [
        (0, "Le diagnostic vérifie données (SHA-256), outils, serveur Ollama, modèle, vitesse réelle et mémoire.", BLEU),
        (10, "Ici : 23 jetons/s ; le modèle tient à 86 % sur la carte graphique (avertissement expliqué).", ORANGE)],
        maintien=8))
    cycle = [l for l in lire("cycle_complet_qwen3_4b.txt") if not l.startswith("Votre choix")]
    s.append(rejeu(cycle, "Cycle complet avec qwen3:4b (exemple_chiffre.txt)", 0, [
        (0, "Classifieur : il appelle ses deux outils (IC, fréquences). IC = 0,051 : chiffre polyalphabétique.", BLEU),
        (21 * 0.8, "Cryptanalyste : Kasiski, Friedman puis attaque_vigenere. La clé VERNE est calculée par le code.", BLEU),
        (52 * 0.8, "Linguiste : score de quadrigrammes 0,976, le clair est jugé plausible.", VERT),
        (64 * 0.8, "Pédagogue : explication pas à pas, rédigée uniquement à partir des valeurs des traces.", BLEU),
        (78 * 0.8, "Vérificateur : exercice avec une nouvelle clé (SOLIS), chiffré puis cassé par les outils : "
                   "corrigé vérifié.", VERT),
        (91 * 0.8, "91 s au total, 5 agents, aucun repli ni appel refusé.", VERT)], echelle=0.8, maintien=14))
    fin = cycle[cycle.index("CLAIR :"):] if "CLAIR :" in cycle else cycle[-8:]
    im, d = base("Résultat : texte clair et explication du Pédagogue")
    y = 82
    for l in fin:
        for m in textwrap.wrap(l, 92) or [""]:
            d.text((40, y), m, font=POL["mono18"], fill=ENCRE if not l.endswith(":") else BLEU)
            y += 25
    legende(d, "L'explication cite les vraies valeurs (IC, longueur de clé, score) ; sa qualité est notée sur "
               "10 explications tirées au hasard.")
    s.append([(im, 22)])
    s.append([(diapo("Sécurité du système multi-agents (modèle de menace STRIDE)", [
        "Liste fermée d'outils par agent : contrôlée avant exécution ET imposée au décodage (schéma JSON).",
        "Le texte chiffré n'est jamais un argument fourni par le modèle ; le clair vient d'un résultat d'outil "
        "désigné par identifiant (R1, R2...).",
        "Garde-fou : un « plausible » du Linguiste est refusé sous un score de 0,65 (mesuré : bons clairs ≥ 0,70, "
        "faux ≤ 0,62).",
        "Expériences dédiées : pannes injectées (délais, JSON invalide, outils en échec) et injection de consignes "
        "dans les sorties d'outils.",
    ], couleur=ORANGE, cap="Injection de consignes, donnée piégée, appel d'outil halluciné : contre-mesures testées "
                           "automatiquement et mesurées."), 24)])
    trace = lire("trace_qwen3_0.6b_boucle_cesar.txt")
    s.append(rejeu(trace, "Les traces servent à corriger le système (qwen3:0.6b)", 0, [
        (0, "Avec un très petit modèle, le Classifieur se trompe (« mono ») : c'est une décision du modèle, autorisée.",
         ORANGE),
        (12, "Le garde-fou refuse les « plausible » à 0,058... mais le Cryptanalyste relance César quatre fois.",
         ORANGE),
        (36, "Correction apportée : une hypothèse rejetée ne peut plus être reproposée, jusqu'à 6 itérations ; test "
             "automatisé reproduisant cette trace.", VERT)], echelle=0.85, maintien=12))
    evals = lire("evaluation_reduite.txt")
    s.append(rejeu(evals, "Évaluation reproductible : vsquad reproduire --petit", 32, [
        (0, "Une commande enchaîne toutes les expériences : Shannon, longueurs minimales, Kasiski, ablation, "
            "robustesse, pannes, injection, explications.", BLEU),
        (20, "Tout est agrégé dans results/metrics.json, avec figures et page de résultats ; l'exécution est "
             "reprenable.", VERT)], maintien=10))
    s.append(scene_resultats())
    s.append([(diapo("Science ouverte et reproductibilité", [
        "Dépôt public, intégration continue : tests sous Linux, Windows et macOS, image Docker, détection de "
        "secrets, évaluation réduite avec un modèle de 0,6B.",
        "make reproduce / vsquad reproduire : environnement figé (uv.lock), modèles exacts (digest vérifié), "
        "données à graine fixe.",
        "Résultats signés (SHA256SUMS + minisign), AUDIT.md avec tolérances, carte du système, déclaration "
        "d'usage de l'IA.",
        "Version v1.0.0 archivée sur Zenodo avec DOI ; page de résultats publique (GitHub Pages).",
    ], couleur=VERT, cap="Un tiers peut tout vérifier sans contacter l'auteur : make verify, make reproduce, "
                         "make compare."), 26)])
    im, d = base()
    d.rectangle([0, 0, W, 12], fill=BLEU)
    d.text((W // 2, 250), "Le modèle décide et explique ; le code calcule.", font=POL["h"], fill=ENCRE, anchor="mm")
    d.text((W // 2, 320), "github.com/drozanski75/vigenere-squad", font=POL["mono18"], fill=BLEU, anchor="mm")
    d.text((W // 2, 360), "drozanski75.github.io/vigenere-squad", font=POL["mono18"], fill=BLEU, anchor="mm")
    d.text((W // 2, 460), "Dawid Rozanski — M1 Cybersécurité, SUP DE VINCI", font=POL["txt"], fill=ENCRE2,
           anchor="mm")
    d.text((W // 2, 684), SOURCE, font=POL["petit"], fill=ENCRE2, anchor="mm")
    s.append([(im, 12)])
    return s


def scene_resultats() -> list[tuple[Image.Image, float]]:
    m_p = R / "results" / "metrics.json"
    figs = R / "results" / "figures"
    if not m_p.exists():
        return [(diapo("Résultats", ["Les résultats de l'évaluation complète figurent dans results/metrics.json "
                                     "et sur la page de résultats publique."]), 8)]
    m = json.loads(m_p.read_text(encoding="utf-8"))
    r = m.get("resume", {})
    puces = []
    for c, v in sorted(m["experiences"].get("principal", {}).items()):
        ref = v.get("comparaison_reference", {}).get("reference_sur_sous_ensemble", {}).get("moyenne")
        puces.append(f"{c} : {v['taux_exact']['moyenne']:.1f} % de clairs exacts sur {v['n_chiffres']} chiffrés"
                     + (f" (référence sur les mêmes : {ref:.1f} %)" if ref is not None else "")
                     + f", {v['duree_moyenne_s']['moyenne']:.1f} s par chiffré")
    if "kasiski_tete_correcte_autoclave_pct" in r:
        puces.append(f"Kasiski trouve la bonne longueur en tête : {r['kasiski_tete_correcte_vigenere_pct']} % "
                     f"(Vigenère) contre {r['kasiski_tete_correcte_autoclave_pct']} % (autoclave).")
    out = [(diapo("Résultats mesurés (results/metrics.json)", puces,
                  cap="Moyennes sur 3 répétitions ; la comparaison avec la référence sans IA est faite sur les mêmes "
                      "chiffrés."), 22)]
    for nom, titre, cap in [("ablation.png", "Étude d'ablation", "Taux de clair exact et durée par configuration."),
                            ("taux_par_longueur_principal.png", "Succès par procédé et longueur de texte",
                             "Les échecs se concentrent sur les textes courts, en dessous de la distance d'unicité."),
                            ("shannon.png", "Lien avec Shannon",
                             "Longueur minimale de succès à 90 % comparée à la distance d'unicité du français.")]:
        if (figs / nom).exists():
            out.append((image_figure(figs / nom, titre, cap), 14))
    return out


def main() -> None:
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else R / "docs" / "video" / "demo_vigenere_squad.mp4"
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        fichiers = []
        for i, sc in enumerate(scenes()):
            f = tmp / f"scene_{i:02d}.mp4"
            encoder_scene(sc, f, tmp)
            fichiers.append(f)
            print(f"scène {i + 1} : {sum(d for _, d in sc):.0f} s", flush=True)
        (tmp / "concat.txt").write_text("".join(f"file '{f}'\n" for f in fichiers))
        provisoire = sortie.with_name(sortie.stem + ".partiel.mp4")
        sortie.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i",
                        str(tmp / "concat.txt"), "-c", "copy", "-movflags", "+faststart", str(provisoire)],
                       check=True)
        provisoire.rename(sortie)
    duree = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            str(sortie)], capture_output=True, text=True).stdout.strip()
    print(f"{sortie} : {float(duree):.0f} s")


if __name__ == "__main__":
    main()
