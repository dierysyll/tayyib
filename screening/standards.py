"""
Les standards de screening financier.

Il n'existe pas UN screening halal : il existe plusieurs standards, qui ne
retiennent ni les mêmes seuils ni le même dénominateur. Une même société
peut être conforme selon MSCI et non conforme selon AAOIFI, simplement
parce que l'un rapporte la dette au total du bilan et l'autre à la
capitalisation boursière.

C'est précisément ce que les applications concurrentes laissent dans le
flou. Ici le standard est un choix explicite de l'utilisateur, et chaque
verdict affiche le standard qui l'a produit.

Chaque standard décrit :
  - `denominator` : à quoi on rapporte les montants ("market_cap" ou
    "total_assets") ;
  - `ratios`      : les seuils, exprimés en fraction (0.30 = 30 %) ;
  - `note`        : les limites de notre implémentation, affichées à
    l'utilisateur. On ne cache pas les approximations.
"""

# Le seuil de revenus non conformes est commun aux trois standards (5 %),
# mais il n'est PAS calculable à partir de données de marché : il faut
# lire le rapport annuel. Voir screening/engine.py — on ne l'invente pas.
NON_COMPLIANT_INCOME_MAX = 0.05

STANDARDS = {
    "aaoifi": {
        "id": "aaoifi",
        "label": "AAOIFI",
        "full": "AAOIFI — Norme Charia n° 21",
        "denominator": "market_cap",
        "denominator_label": "capitalisation boursière",
        "ratios": {
            "debt": 0.30,
            "liquidity": 0.30,
        },
        "uses_receivables": False,
        "note": (
            "L'AAOIFI rapporte les montants à la capitalisation boursière. "
            "Les seuils sont ceux de la norme n° 21."
        ),
    },
    "djim": {
        "id": "djim",
        "label": "Dow Jones",
        "full": "Dow Jones Islamic Market (DJIM)",
        "denominator": "market_cap",
        "denominator_label": "capitalisation boursière",
        "ratios": {
            "debt": 1 / 3,
            "liquidity": 1 / 3,
            "receivables": 1 / 3,
        },
        "uses_receivables": True,
        "note": (
            "Le DJIM rapporte les montants à la capitalisation boursière "
            "MOYENNE sur 24 mois. Nous utilisons la capitalisation du jour : "
            "sur une valeur très volatile, le verdict peut différer de "
            "l'indice officiel."
        ),
    },
    "msci": {
        "id": "msci",
        "label": "MSCI Islamic",
        "full": "MSCI Islamic Index Series",
        "denominator": "total_assets",
        "denominator_label": "total du bilan",
        "ratios": {
            "debt": 1 / 3,
            "liquidity": 1 / 3,
            "receivables": 1 / 3,
        },
        "uses_receivables": True,
        "note": (
            "MSCI rapporte les montants au total du bilan, et non à la "
            "capitalisation. C'est le standard le plus stable dans le temps, "
            "puisqu'il ne dépend pas du cours de Bourse."
        ),
    },
}

DEFAULT_STANDARD = "aaoifi"

# Libellés des ratios, pour l'affichage.
RATIO_LABELS = {
    "debt": "Dette portant intérêt",
    "liquidity": "Trésorerie et placements",
    "receivables": "Créances clients",
}


def get(standard_id):
    """Le standard demandé, ou le standard par défaut si l'identifiant est
    inconnu (une URL bricolée à la main ne doit pas faire tomber l'appli)."""
    return STANDARDS.get(standard_id, STANDARDS[DEFAULT_STANDARD])
