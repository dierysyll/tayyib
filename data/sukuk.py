"""
Les sukuk cotés à la BRVM.

Pourquoi un compartiment à part
-------------------------------
Le screener de ce site trie des **actions**. Une action est une part
d'entreprise : on peut en examiner l'activité et les comptes, et c'est ce
que font les six standards. Un **sukuk** n'est pas une part d'entreprise,
c'est un certificat adossé à un actif réel, dont la licéité se joue à la
structuration — ijara, murabaha, wakala — et non dans un bilan. Lui
appliquer un ratio de dette rapportée à la capitalisation n'aurait aucun
sens : il n'a ni l'une ni l'autre.

D'où un compartiment séparé, avec ses propres colonnes et sa propre
prudence.

Ce que nous affirmons, et ce que nous n'affirmons pas
-----------------------------------------------------
Notre affirmation est étroite et vérifiable : sur les quelque 270 lignes
obligataires cotées à la BRVM, **cinq sont présentées comme des sukuk par
la Bourse elle-même**, et toutes les autres sont des obligations
classiques à intérêt — donc du riba, et donc hors de portée d'un
épargnant musulman. Distinguer les cinq des autres est un service que
personne ne rend en Afrique de l'Ouest, et il ne demande aucune
compétence religieuse.

Nous ne certifions rien de plus. Nous ne relisons pas la documentation
d'émission, nous n'évaluons pas la structure, et nous ne nous prononçons
pas sur la conformité d'un titre donné. Ces sukuk ont été structurés avec
un conseil de conformité à l'émission ; c'est cette parole-là qui engage,
pas la nôtre.

Ce que la source publie mal
---------------------------
La colonne « date de maturité » est **vide pour les cinq**, et la date
d'émission affiche le 17/10/2016 pour toutes — c'est la date de saisie à
la BRVM, pas celle des émissions, dont deux sont antérieures. L'intitulé,
lui, porte la période : « SUKUK ETAT DU SENEGAL 6% 2016-2026 ». C'est
donc lui que nous lisons, et la date du dernier coupon versé qui dit si
le titre vit encore.
"""

import html
import re
import urllib.request
from datetime import date

OBLIGATIONS = "https://www.brvm.org/fr/cours-obligations/0"

ENTETES = {
    "User-Agent": "Mozilla/5.0 (compatible; Tayyib/1.0; +https://tayyib.app)",
    "Accept": "text/html,application/xhtml+xml",
}

BALISES = re.compile(r"<[^>]+>")
EST_SUKUK = re.compile(r"sukuk", re.I)

# « SUKUK ETAT DU SENEGAL 6% 2016-2026 » : l'émetteur, le taux facial, la
# période. Le taux s'écrit « 6% » ou « 5,75% » selon les lignes.
INTITULE = re.compile(
    r"^SUKUK\s+(?P<emetteur>.+?)\s+"
    r"(?P<taux>\d+(?:[.,]\d+)?)\s*%\s+"
    r"(?P<debut>\d{4})\s*-\s*(?P<fin>\d{4})\s*$",
    re.I,
)

# Le pays de l'État émetteur, déduit du code : SUKSN → Sénégal. L'article
# est stocké avec lui : « État du Sénégal » mais « État de Côte d'Ivoire »,
# et aucune règle simple ne s'en déduit.
PAYS = {
    "SN": ("Sénégal", "du"), "CI": ("Côte d'Ivoire", "de"),
    "TG": ("Togo", "du"), "BF": ("Burkina Faso", "du"),
    "ML": ("Mali", "du"), "NE": ("Niger", "du"),
    "BJ": ("Bénin", "du"), "GW": ("Guinée-Bissau", "de"),
}


def _nombre(texte):
    """Un montant francophone — « 10 300 », « 295,00 » — en flottant."""
    if not texte:
        return None
    propre = (texte.replace(" ", "").replace(" ", "")
                   .replace(" ", "").replace(",", "."))
    try:
        return float(propre)
    except ValueError:
        return None


def _lignes(tableau):
    """Les lignes du tableau, cellules nettoyées, en-tête écarté."""
    for tr in re.findall(r"<tr.*?</tr>", tableau, re.S)[1:]:
        cellules = [
            re.sub(r"\s+", " ", html.unescape(BALISES.sub(" ", c))).strip()
            for c in re.findall(r"<td.*?</td>", tr, re.S)
        ]
        if len(cellules) >= 6:
            yield cellules


def collecte(aujourdhui=None):
    """Les sukuk cotés, et le nombre total de lignes obligataires.

    Renvoie (sukuk, total). Le total sert à dire au lecteur combien de
    lignes il aurait fallu écarter : « cinq sur deux cent soixante-neuf »
    est une information, « cinq » tout seul n'en est pas une.
    """
    aujourdhui = aujourdhui or date.today()
    requete = urllib.request.Request(OBLIGATIONS, headers=ENTETES)
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        page = reponse.read().decode("utf-8", "ignore")

    tableaux = [t for t in re.findall(r"<table.*?</table>", page, re.S)
                if "Code obligation" in t]
    if not tableaux:
        return [], 0

    titres, total = [], 0
    for cellules in _lignes(tableaux[0]):
        total += 1
        code, intitule = cellules[0].strip(), cellules[1].strip()
        if not EST_SUKUK.search(intitule):
            continue

        lu = INTITULE.match(intitule)
        # Le code porte le pays de l'émetteur : SUKSN → SN. C'est aussi le
        # code ISO qu'affichent les pastilles du site, d'où sa conservation
        # telle quelle — le déduire du nom français donnerait « SE ».
        iso = code[3:5].upper() if code.upper().startswith("SUK") else None
        pays, article = PAYS.get(iso) or (None, None)
        fin = int(lu.group("fin")) if lu else None

        titres.append({
            "code": code,
            "intitule": intitule,
            "emetteur": f"État {article} {pays}" if pays else None,
            "pays": pays,
            "code_pays": iso if pays else None,
            "taux": _nombre(lu.group("taux")) if lu else None,
            "debut": int(lu.group("debut")) if lu else None,
            "fin": fin,
            "cours": _nombre(cellules[4]),
            "coupon_couru": _nombre(cellules[5]),
            "dernier_paiement": _paiement(cellules[6] if len(cellules) > 6 else ""),
            # L'échéance n'est connue qu'à l'année près : l'intitulé ne dit
            # pas le jour, et la colonne prévue pour lui est vide. On ne
            # tranche donc pas l'année en cours.
            "echu": bool(fin and fin < aujourdhui.year),
            "derniere_annee": bool(fin and fin == aujourdhui.year),
        })

    titres.sort(key=lambda t: (t["echu"], -(t["fin"] or 0), t["code"]))
    return titres, total


def _paiement(cellule):
    """« 26/01/2026 / 301,67 » → {date, montant}, ou None."""
    lu = re.match(r"\s*(\d{2}/\d{2}/\d{4})\s*/\s*(.+?)\s*$", cellule)
    if not lu:
        return None
    return {"date": lu.group(1), "montant": _nombre(lu.group(2))}
