"""
Graphiques en SVG, calculés côté serveur.

Pas de bibliothèque de graphiques : le rendu tient en quelques dizaines de
lignes de projection, et une page qui charge 300 Ko de JavaScript pour
tracer une ligne serait plus lourde que tout le reste du site réuni.

Le graphique de cours n'est pas décoratif. On y superpose les arrêtés
comptables, coloriés selon le verdict de conformité de l'exercice — le
lecteur voit d'un coup d'œil *quand* une valeur est sortie ou revenue dans
les seuils, et à quel niveau de cours. C'est le genre de lecture que ni
Zonebourse (qui ignore la conformité) ni les screeners halal (qui ignorent
le cours) ne permettent.
"""

LARGEUR = 720
HAUTEUR = 200
MARGE_HAUT = 14
MARGE_BAS = 22


def courbe_cours(cours, jalons=None):
    """Projette une série de cours en coordonnées SVG.

    `cours`   : liste de [date_iso, valeur], du plus ancien au plus récent.
    `jalons`  : liste de {"date": iso, "verdict": ...} à placer sur la
                courbe (les arrêtés comptables).

    Renvoie None si la série est trop courte pour être tracée — l'appelant
    n'affiche alors pas de graphique, plutôt qu'un trait plat trompeur.
    """
    points = [(d, v) for d, v in (cours or []) if v is not None]
    if len(points) < 8:
        return None

    valeurs = [v for _, v in points]
    bas, haut = min(valeurs), max(valeurs)
    if haut == bas:
        return None

    hauteur_utile = HAUTEUR - MARGE_HAUT - MARGE_BAS

    def x_de(i):
        return i / (len(points) - 1) * LARGEUR

    def y_de(v):
        return MARGE_HAUT + (haut - v) / (haut - bas) * hauteur_utile

    coords = [(x_de(i), y_de(v)) for i, (_, v) in enumerate(points)]

    ligne = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    aire = (
        f"M{coords[0][0]:.1f},{HAUTEUR - MARGE_BAS} "
        + "L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in coords)
        + f" L{coords[-1][0]:.1f},{HAUTEUR - MARGE_BAS} Z"
    )

    # Repères d'année : le premier point de chaque année civile.
    annees, vues = [], set()
    for i, (d, _) in enumerate(points):
        annee = d[:4]
        if annee not in vues:
            vues.add(annee)
            annees.append({"annee": annee, "x": x_de(i)})

    # Jalons : on cherche l'indice du point le plus proche de chaque arrêté.
    reperes = []
    for jalon in (jalons or []):
        cible = jalon.get("date")
        if not cible:
            continue
        indice = None
        for i, (d, _) in enumerate(points):
            if d <= cible:
                indice = i
            else:
                break
        if indice is None:
            continue
        reperes.append({
            "x": coords[indice][0],
            "y": coords[indice][1],
            "verdict": jalon.get("verdict"),
            "annee": cible[:4],
            "cours": points[indice][1],
        })

    return {
        "largeur": LARGEUR,
        "hauteur": HAUTEUR,
        "ligne": ligne,
        "aire": aire,
        "bas": bas,
        "haut": haut,
        "premier": points[0][1],
        "dernier": points[-1][1],
        "variation": (points[-1][1] - points[0][1]) / points[0][1],
        "annees": annees,
        "reperes": reperes,
        "base_y": HAUTEUR - MARGE_BAS,
    }
