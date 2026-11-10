# Journal des versions de prompts

Chaque modification d'un prompt incrémente sa version (en-tête du fichier) et
est consignée ici avec son effet mesuré sur les métriques (`results/metrics.json`).
La version et l'empreinte SHA-256 de chaque prompt sont enregistrées dans
chaque trace (`debut_agent`).

| Date | Agent | Version | Modification | Effet mesuré |
|---|---|---|---|---|
| 2026-11-10 | tous | 1.0.0 | Version initiale | Référence (voir metrics.json) |
| 2026-11-10 | tous | 1.1.0 | Réponses courtes (pensée ≤ 120 car., justification ≤ 240 car., schéma `maxLength`) ; appels d'outils groupés en une réponse ; budget de jetons 256 (Pédagogue 900) ; contexte 3 072 | Essai sur `exemple_chiffre.txt` (Windows, qwen3:4b, 17 %/83 % CPU/GPU) : v1.0.0 = 252 s pour Classifieur + Cryptanalyste (6 appels, 30-60 s chacun), comportement correct (clé VERNE, 0 refus, 0 repli). Effet de la v1.1.0 : voir metrics.json |
| 2026-11-10 | tous | 1.2.0 | Protocole en deux phases (1er tour : appels seuls, sans conclusion à générer) ; schéma Ollama sans `$defs` imbriqués ; Cryptanalyste : attaque obligatoire dès la 1re réponse, appels répétés non recalculés, rappel des identifiants disponibles | Essai v1.1.0 (Windows, qwen3:4b, 85 % GPU) : cycle complet 195 s, clé VERNE retrouvée ; mais Cryptanalyste en boucle (kasiski/friedman ×3 sans attaque, puis identifiant R1 inventé → repli) et Pédagogue en erreur HTTP 400 (schéma `$ref` invalide) → repli. Effet de la v1.2.0 : voir metrics.json |
| 2026-11-10 | pédagogue, vérificateur (version commune 1.3.0) | 1.3.0 | Pédagogue : lecture correcte de l'IC et de l'estimation de Friedman, longueur de clé fournie ; Vérificateur : `casser_exercice` sans argument (arguments superflus ignorés) ; contexte 2 048 jetons avec détection de saturation | Essai v1.2.0 : cycle complet correct en 192 s (5 agents, 0 repli) ; explication fausse sur deux points (IC « clé courte », Friedman pris pour la longueur) ; exercice non validé (argument `cle` refusé par `casser_exercice`) ; modèle 85 % GPU. Effet de la v1.3.0 : voir metrics.json |
| 2026-11-10 | orchestrateur (prompts inchangés, 1.3.0) | — | Garde-fou : un procédé déjà rejeté ne peut être reproposé (repli sur l'hypothèse suivante) ; `iterations_max` 4 → 6 ; seuil du garde-fou de plausibilité 0,45 → 0,65 (mesuré sur le corpus) | Évaluation réduite avec qwen3:0.6b : Cryptanalyste relançant 4 fois César sur un Vigenère (boucle épuisée, échec) ; Linguiste déclarant « plausible » des clairs faux |
