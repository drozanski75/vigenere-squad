"""Empreintes SHA-256 des artefacts publiés et signature minisign.

  python scripts/signature.py cle       # crée la paire de clés (secrète hors dépôt)
  python scripts/signature.py empreintes  # écrit SHA256SUMS
  python scripts/signature.py signer    # écrit SHA256SUMS.minisig
  python scripts/signature.py verifier  # vérifie signature + empreintes

Format compatible avec l'outil officiel :
  minisign -Vm SHA256SUMS -p minisign.pub   puis   sha256sum -c SHA256SUMS
La clé secrète est lue dans $MINISIGN_SECRET_KEY (défaut ~/.minisign/vigenere-squad.key),
son mot de passe dans $MINISIGN_PASSWORD (sinon demandé).
"""
from __future__ import annotations

import getpass
import hashlib
import os
import sys
from pathlib import Path

import minisign

RACINE = Path(__file__).resolve().parents[1]
PUB = RACINE / "minisign.pub"
SUMS = RACINE / "SHA256SUMS"
SIG = RACINE / "SHA256SUMS.minisig"
CLE = Path(os.environ.get("MINISIGN_SECRET_KEY", Path.home() / ".minisign" / "vigenere-squad.key"))

# Artefacts publiés couverts par l'empreinte
MOTIFS = ["results/metrics.json", "results/ENVIRONMENT.json", "results/EXECUTION.json", "results/raw/**/*.jsonl", "results/figures/*.png",
          "results/explications_echantillon.md", "results/notes_explications.csv", "data/corpus/*.jsonl",
          "data/sources.json", "config/experiment.yaml", "uv.lock", "docs/rapport.pdf", "traces/**/*.jsonl"]


def fichiers() -> list[Path]:
    vus = set()
    for m in MOTIFS:
        vus.update(p for p in RACINE.glob(m) if p.is_file())
    return sorted(vus, key=lambda p: p.relative_to(RACINE).as_posix())


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def ecrire_empreintes() -> int:
    lignes = [f"{sha256(p)}  {p.relative_to(RACINE).as_posix()}" for p in fichiers()]
    SUMS.write_text("\n".join(lignes) + "\n", encoding="utf-8", newline="\n")
    return len(lignes)


def _mot_de_passe(confirmer=False) -> str:
    mdp = os.environ.get("MINISIGN_PASSWORD")
    if mdp is None:
        mdp = getpass.getpass("Mot de passe de la clé minisign : ")
        if confirmer and getpass.getpass("Confirmer : ") != mdp:
            sys.exit("mots de passe différents")
    return mdp


def creer_cle() -> None:
    if CLE.exists():
        sys.exit(f"{CLE} existe déjà ; supprimez-la volontairement pour en recréer une.")
    kp = minisign.KeyPair.generate()
    kp.secret_key.encrypt(_mot_de_passe(confirmer=True))
    CLE.parent.mkdir(parents=True, exist_ok=True)
    CLE.write_bytes(bytes(kp.secret_key))
    CLE.chmod(0o600)
    PUB.write_bytes(bytes(kp.public_key))
    print(f"clé secrète : {CLE} (NE PAS la publier) ; clé publique : {PUB}")


def signer() -> None:
    sk = minisign.SecretKey.from_file(CLE)
    if sk.is_encrypted():
        sk.decrypt(_mot_de_passe())
    sig = sk.sign(SUMS.read_bytes(), trusted_comment="vigenere-squad v1.0.0 SHA256SUMS")
    SIG.write_bytes(bytes(sig))
    print(f"signature écrite : {SIG.name}")


def empreinte_cle() -> str:
    return hashlib.sha256(PUB.read_bytes().strip().splitlines()[-1]).hexdigest()


def verifier() -> bool:
    pk = minisign.PublicKey.from_file(PUB)
    pk.verify(SUMS.read_bytes(), minisign.Signature.from_file(SIG))
    print(f"signature valide (clé publique {PUB.read_text(encoding="utf-8").splitlines()[-1]})")
    erreurs = 0
    for l in SUMS.read_text(encoding="utf-8").splitlines():
        h, nom = l.split("  ", 1)
        p = RACINE / nom
        if not p.exists() or sha256(p) != h:
            print(f"ÉCHEC {nom}")
            erreurs += 1
    print(f"{len(SUMS.read_text(encoding="utf-8").splitlines())} fichiers vérifiés, {erreurs} écart(s)")
    return erreurs == 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "verifier"
    if action == "cle":
        creer_cle()
    elif action == "empreintes":
        print(f"{ecrire_empreintes()} fichiers -> SHA256SUMS")
    elif action == "signer":
        signer()
    elif action == "empreinte-cle":
        print(empreinte_cle())
    else:
        sys.exit(0 if verifier() else 1)
