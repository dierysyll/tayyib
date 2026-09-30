"""
La note de marge de conformité.

Ce qu'elle mesure, et ce qu'elle ne mesure pas
----------------------------------------------
Deux sociétés peuvent être « conformes » et ne pas l'être de la même façon.
L'une porte une dette à 4 % de sa capitalisation, l'autre à 29,8 % pour un
seuil à 30 % : la première le restera après une baisse de moitié du cours,
la seconde bascule au premier accroc. Le verdict binaire ne dit rien de
cette différence, et c'est pourtant ce que veut savoir quelqu'un qui achète
pour plusieurs années.

La note comble ce trou, et rien d'autre. **Ce n'est pas une note de qualité
d'investissement.** Elle ne dit rien de la rentabilité, de la valorisation,
de la gouvernance ni des perspectives d'une société. Un A+ signifie « très
loin des seuils du standard », pas « bonne action ». Une entreprise en perte,
surévaluée et mal dirigée peut parfaitement obtenir A+ si elle n'a pas de
dette.

C'est une distinction que les notations concurrentes laissent volontiers
floue, parce qu'une lettre ressemble à un avis. Ici elle est écrite en toutes
lettres partout où la note apparaît.

Comment elle est calculée
-------------------------
Pour chaque ratio du standard, on regarde la **tension** : le montant rapporté
à son seuil. 0,15/0,30 donne une tension de 0,50 — le ratio consomme la moitié
de la marge autorisée. On retient la tension la plus forte des ratios, celle
qui contraint réellement, et la note en découle.

Aucune note n'est attribuée aux valeurs non conformes ni à celles laissées
« à vérifier » : dans le premier cas la question ne se pose plus, dans le
second on n'a pas les chiffres pour y répondre.
"""

from screening import engine

# Tension maximale admise pour chaque note. Les paliers sont resserrés en
# haut de l'échelle : passer de 90 % à 95 % de la marge consommée change
# beaucoup moins la situation que passer de 10 % à 20 %.
PALIERS = [
    (0.20, "A+"),
    (0.35, "A"),
    (0.50, "A−"),
    (0.62, "B+"),
    (0.72, "B"),
    (0.80, "B−"),
    (0.88, "C+"),
    (0.94, "C"),
    (1.00, "C−"),
]

# Regroupement pour la couleur : on ne veut pas neuf teintes à l'écran.
FAMILLES = {"A": "haute", "B": "moyenne", "C": "faible"}

RESUMES = {
    "haute": "Large marge sous les seuils : la conformité résisterait à un mouvement de marché important.",
    "moyenne": "Marge confortable, mais un endettement supplémentaire ou une forte baisse du cours la réduirait.",
    "faible": "Marge étroite : la valeur est près de basculer, et un simple mouvement de cours peut suffire.",
}


def tension(resultat):
    """La part de marge consommée par le ratio le plus contraignant.

    Renvoie None si aucun ratio n'est calculable — on ne note pas ce qu'on
    ne peut pas mesurer.
    """
    tensions = [
        r["valeur"] / r["seuil"]
        for r in resultat.get("ratios", [])
        if r.get("valeur") is not None and r.get("seuil")
    ]
    return max(tensions) if tensions else None


def note(resultat):
    """La note d'une évaluation, ou None si elle n'a pas lieu d'être.

    Renvoie un dictionnaire : lettre, famille (pour la couleur), tension et
    marge restante en pourcentage.
    """
    if resultat.get("verdict") != engine.CONFORME:
        return None

    t = tension(resultat)
    if t is None:
        return None

    lettre = next((l for seuil, l in PALIERS if t <= seuil), "C−")
    famille = FAMILLES[lettre[0]]

    return {
        "lettre": lettre,
        "famille": famille,
        "tension": t,
        "marge": max(0.0, 1 - t),
        "resume": RESUMES[famille],
    }


def note_de(societe, standard_id):
    """Raccourci : évalue puis note."""
    return note(engine.evaluate(societe, standard_id))
