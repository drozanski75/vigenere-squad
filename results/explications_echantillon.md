# Explications du Pédagogue (échantillon aléatoire, graine fixe)

Notation : voir docs/grille_explications.md ; saisir les notes dans results/notes_explications.csv


## 1. standard-beaufort-0300-3 (procédé réel : beaufort, clé réelle : NXVSRKT)

Résultat : beaufort / clé NXVSRKT / clair exact

1. L'IC de 0.03946 est nettement inférieur à 0.078, confirmant un chiffre polyalphabétique (pas de monoalphabétique). 2. Kasiski (longueurs [7,4,2,19,20,17]) et Friedman (estimation 34.78, longueurs [7,14,20,8,10,5]) indiquent une clé de 7 lettres. 3. La clé 'NXVSRKT' a été trouvée via des méthodes de décalage et validée par un score normalisé de 0.962. 4. Le texte de 300 lettres est suffisamment long pour une analyse précise.


Exercice proposé : `{"procede": "beaufort", "cle": "QWERTYUI", "enonce": "CHIFFRE AVEC BEAUFORT : DECRYPTE LE TEXTE 'GZACJXKTDNREPYFQSBHIVWULOM' EN UTILISANT UNE CLÉ DE 7 LETTRES"}` — corrigé vérifié par les outils : True


## 2. standard-cesar-2000-3 (procédé réel : cesar, clé réelle : 3)

Résultat : vigenere / clé D / clair exact

1. L'IC de 0.07297 est proche de 0.078, ce qui indique un chiffre polyalphabétique (pas monoalphabétique). Les fréquences ordinales 'HDLWXVQOURFGPSYJTIKEAMBCZN' montrent une distribution non standard.
2. La longueur de clé est identifiée à 1 par 'longueur_cle_trouvee', tandis que Friedman donne une estimation grossière (1.14) sans précision.
3. La clé 'D' a été trouvée via Vigenère avec un score normalisé de 0.945, validé par une clair cohérent.
4. Le texte de 2000 lettres est court pour une clé de 1, ce qui rend la difficulté élevée.


Exercice proposé : `{"procede": "vigenere", "cle": "K", "enonce": "CHIFFRE VIGENERE AVEC CLÉ 'K' : DECRYPTE LE TEXTES 'HDLWXVQOURFGPSYJTIKEAMBCZN' (2000 lettres) pour obtenir le début du clair."}` — corrigé vérifié par les outils : True


## 3. standard-cesar-0150-1 (procédé réel : cesar, clé réelle : 7)

Résultat : cesar / clé 7 / clair exact

1. L'IC de 0.0894 est proche de 0.078, ce qui indique un chiffre polyalphabétique (pas monoalphabétique). Les fréquences sont 'LZHUKVABSYWCPIJTFMNXDEGOQR'.
2. Le procédé est 'cesar' (cesar) avec une clé de longueur 1, identifié par hypothèse.
3. La clé '7' a été retrouvée par force brute (comme pour le chiffre de César) et le clair commence par 'PASSEPARTOUT...' ce qui est valide.
4. Le texte est de 150 lettres, ce qui est assez court pour une analyse polyalphabétique.


Exercice proposé : `{"procede": "cesar", "cle": "12", "enonce": "Chiffre le texte 'PASSEPARTOUT SE TROUVA D'ABORD DANS UNE CITE ABSOLUMENT EUROPEENNE, AVEC DES MAISONS A BASSES FACADES, ORNEES DE VERANDA' avec la clé 12."}` — corrigé vérifié par les outils : True


## 4. standard-vigenere-0300-0 (procédé réel : vigenere, clé réelle : XHFYASNZKIFW)

Résultat : vigenere / clé XHFYASNZKIFW / clair exact

1. L'IC de 0.04069 est nettement inférieur à 0.078, confirmant un chiffre polyalphabétique (pas monoalphabétique). Les fréquences ordinales 'CBZMNSWAKQJIPVOYDRXHTUGELF' montrent une distribution non uniforme.
2. Kasiski a identifié des répétitions à 3, 12, 6, 4, 2, 13 lettres, mais Friedman estime 16.72 (ordre de grandeur). La longueur de clé trouvée est 12.
3. La clé 'XHFYASNZKIFW' a été retrouvée via Vigenère avec un score normalisé de 0.919, validé par un début de clair cohérent.
4. Le texte de 300 lettres est suffisant pour une clé de 12, évitant les erreurs de statistiques.


Exercice proposé : `{"procede": "vigenere", "cle": "MATHS", "enonce": "CHIFFREZ LE TEXTE : 'LE CHIEN EST AU JARDI' EN VIGENERE AVEC LA CLE 'MATHS'."}` — corrigé vérifié par les outils : True


## 5. standard-vigenere-0080-2 (procédé réel : vigenere, clé réelle : TYWOADKUNUUE)

Résultat : vigenere / clé TYWOADKUNUUE / clair exact

1. L'IC (0.04367) est nettement bas (inférieur à 0.078), confirmant un chiffre polyalphabétique. Les fréquences ordinales (IOCGNXAMTEHRVWYBFJQZDKPULS) montrent une distribution non uniforme.
2. Kasiski n'a pas été utilisé (longueurs vides) mais Friedman estime une clé de longueur ~7,2, ce qui s'aligne avec la longueur trouvée (12) après vérification.
3. La clé (TYWOADKUNUUE) a été trouvée via Vigenère avec un score normalisé de 0.954, validé par un début de clair cohérent.
4. Le texte (80 lettres) est court, rendant la détection de la clé difficile mais la longueur trouvée (12) est plausible.


Exercice proposé : `{"procede": "vigenere", "cle": "XKZQVJ", "enonce": "Chiffre le texte suivant avec Vigenère : 'CHIFFREZ VOTRE MESSAGE AVEC UNE CLÉ DE 5 LETTRES' (utilisez la clé 'XKZQVJ')"}` — corrigé vérifié par les outils : True


## 6. standard-affine-2000-2 (procédé réel : affine, clé réelle : 5,15)

Résultat : affine / clé 5,15 / clair exact

1. L'IC de 0.07475 est proche de 0.078, ce qui confirme un chiffre polyalphabétique (l'IC ne donne pas la longueur de la clé).
2. La longueur de clé a été identifiée via Kasiski (longueurs [2,3,4,5,6,7]) et Friedman (estimation 1.08 avec longueurs [1,2,3]), mais la clé trouvée est '5,15' (affine).
3. La clé '5,15' a été retrouvée par l'hypothèse 'affine' avec un score normalisé de 0.97, validée par un clair cohérent début : 'ET ELLE JURAIT...'.
4. Le texte de 2000 lettres est long, ce qui rend la cryptanalyse difficile mais possible avec des méthodes précises.


Exercice proposé : `{"procede": "affine", "cle": "12,7", "enonce": "Chiffre l'énigme suivante avec la clé affine (a=12, b=7) : 'ET ELLE JURAIT QU'ELLE NE SE MOQUAIT PAS, QUAND UN COUP DE CANON RETENTIT; AUSSITOT, ON SE POUSSA, PELE-MELE, VERS LE VI'"}` — corrigé vérifié par les outils : False


## 7. standard-affine-0150-0 (procédé réel : affine, clé réelle : 3,13)

Résultat : substitution / clé NQTWZCFILORUXADGJMPSVYEBKH / clair exact

L'IC de 0.08438 est nettement bas (inférieur à 0.078), confirmant un chiffre polyalphabétique. Les longueurs de clé trouvées par Kasiski (4, 2, 3, 5, 16, 8) et Friedman (8, 16, 13, 15, 7, 9) convergent vers 13. La clé 'NQTWZCFILORUXADGJMPSVYEBKH' a été retrouvée via des tests de fréquence et validation par le début du clair 'UNE JEUNE PERSONNE BLONDE...'. Le score normalisé de 1.04 valide la clé.


Exercice proposé : `{"procede": "substitution", "cle": "XKJLZMNBQVYRTHWUPOIAFSGC", "enonce": "Chiffre la phrase suivante avec la clé : 'UNE JEUNE PERSONNE BLONDE SE TENAIT A COTE, DANS UNE CHAISE A DOSSIER LONG; ET DES MESSIEURS, QUI AVAIENT UNE PETITE FLE"}` — corrigé vérifié par les outils : False


## 8. standard-cesar-2000-1 (procédé réel : cesar, clé réelle : 16)

Résultat : vigenere / clé Q / clair exact

L'IC de 0.07449 est proche de 0.078, ce qui confirme un chiffre polyalphabétique (pas monoalphabétique). Les fréquences 'UQYKIDJHEBCTFSVZGLRXWNOAPM' montrent une permutation. Kasiski indique des longueurs de répétition [2,3,4,6,5,8] mais la longueur de clé trouvée est 1. Friedman estime 1.09 (ordre de grandeur) avec [1,2,3]. La clé 'Q' a été trouvée par Vigenère et valide le début 'AU BOUT DE TROIS MOIS...' avec score 0.956.


Exercice proposé : `{"procede": "vigenere", "cle": "R", "enonce": "CHIFFRE VIGENERE AVEC UNE CLÉ DE 1 LETTRE : DECRYPTE LE TEXTE 'QZTJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJHJZJH"}` — corrigé vérifié par les outils : True


## 9. standard-beaufort-1000-3 (procédé réel : beaufort, clé réelle : GDDJLEG)

Résultat : beaufort / clé GDDJLEG / clair exact

L'IC de 0.04272 (nettement inférieur à 0.078) confirme un chiffre polyalphabétique. Les fréquences ordonnées 'VSLAZCDPMRYGHJQTENKFOBUWXI' montrent une clé de 7 lettres. Kasiski (longueurs [7, 2, 3, 14, 4, 6]) et Friedman (estimation 9.16) indiquent que la longueur de clé est 7. La clé 'GDDJLEG' a été trouvée avec un score normalisé de 0.987, validée par un clair cohérent : 'ON VOIT ASSEZ QUELLE SUPERIORITE PRODIGIEUSE ELLE DEVAIT AVOIR SUR CES CAILLOUX ET SUR CE SABLE QUE NOUS NOMMONS OR ET P'.


Exercice proposé : `{"procede": "beaufort", "cle": "XKZ", "enonce": "CHIFFRE EN BEAUFORT AVEC CLÉ 'XKZ' : DEBUT DU CLAIR 'ON VOIT ASSEZ QUELLE SUPERIORITE PRODIGIEUSE ELLE DEVAIT AVOIR SUR CES CAILLOUX ET SUR CE SABLE QUE NOUS NOMMONS OR ET P'"}` — corrigé vérifié par les outils : True


## 10. standard-substitution-0600-4 (procédé réel : substitution, clé réelle : PAOQIZVEUHRLKWCSGBXNYFMTJD)

Résultat : substitution / clé PAOQIZVEUHRLKWCSGBXNYFMTJD / clair exact

1. L'IC de 0.07371 est proche de 0.078, indiquant un chiffre polyalphabétique (pas monoalphabétique). Les fréquences ordonnées montrent un motif de chiffrement.
2. Kasiski (longueurs [2,4,3,5,13,7]) et Friedman (estimation 1.12) ont été utilisés pour estimer la longueur de clé, mais l'estimation de Friedman est grossière.
3. La clé 'PAOQIZVEUHRLKWCSGBXNYFMTJD' a été retrouvée par essais (hypotheses_essayees) et validée par un score normalisé de 0.961.
4. Le texte est long (600 lettres), ce qui rend la cryptanalyse difficile mais possible avec des méthodes statistiques.


Exercice proposé : `{"procede": "substitution", "cle": "XKZJYB", "enonce": "Chiffre le texte suivant avec la clé 'XKZJYB' : 'LA VIE EST UNE AVENTURE'."}` — corrigé vérifié par les outils : False
