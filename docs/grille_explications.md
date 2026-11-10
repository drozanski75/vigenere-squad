# Grille de notation des explications du Pédagogue (sur 10)

Dix explications sont tirées au hasard (graine fixe) par `make evaluate`
(`results/explications_echantillon.md`). Chacune est notée selon la grille
ci-dessous ; les notes sont saisies dans `results/notes_explications.csv`
puis agrégées dans `metrics.json` (`explications.notes_grille`).

| Critère | Points | 0 | 1 | 2 |
|---|---|---|---|---|
| Exactitude des valeurs | 2 | valeur inventée ou fausse | une imprécision | toutes les valeurs proviennent des traces |
| Démarche d'identification | 2 | absente | partielle | IC/fréquences/Kasiski/Friedman correctement interprétés |
| Récupération de la clé | 2 | absente ou fausse | évoquée | méthode (χ², force brute, recuit) correctement expliquée |
| Clarté pour un étudiant de L1 | 2 | confuse | compréhensible | étapes ordonnées, vocabulaire défini |
| Exercice proposé | 2 | absent ou invalide | valide mais mal énoncé | valide (corrigé vérifié) et bien énoncé |

Le correcteur note sans connaître le modèle quand c'est possible (anonymiser
les blocs avant notation).
