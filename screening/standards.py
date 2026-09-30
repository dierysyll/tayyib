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
    "total_assets"), sous deux formes : le libellé nu pour les tableaux,
    et le complément tout fait pour les phrases — « à la » capitalisation,
    mais « au » total du bilan, et aucune règle simple ne s'en déduit ;
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
        "denominator_complement": "à la capitalisation boursière",
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
        "denominator_complement": "à la capitalisation boursière",
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
        "denominator_complement": "au total du bilan",
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
    "sp": {
        "id": "sp",
        "label": "S&P Shariah",
        "full": "S&P Dow Jones Shariah Indices",
        "denominator": "market_cap",
        "denominator_label": "capitalisation boursière",
        "denominator_complement": "à la capitalisation boursière",
        "ratios": {
            "debt": 0.33,
            "liquidity": 0.33,
            "receivables": 0.49,
        },
        "uses_receivables": True,
        "note": (
            "S&P retient la capitalisation moyenne sur 36 mois, là où nous "
            "utilisons celle du jour. Sa particularité est le seuil de "
            "créances, nettement plus permissif (49 %) que celui du Dow "
            "Jones — un même distributeur peut passer ici et échouer là."
        ),
    },
    "ftse": {
        "id": "ftse",
        "label": "FTSE Shariah",
        "full": "FTSE Shariah Global Equity Index Series",
        "denominator": "total_assets",
        "denominator_label": "total du bilan",
        "denominator_complement": "au total du bilan",
        "ratios": {
            "debt": 1 / 3,
            "liquidity": 1 / 3,
            "receivables": 0.50,
        },
        "uses_receivables": True,
        "note": (
            "FTSE, comme MSCI, rapporte au total du bilan, mais tolère "
            "jusqu'à 50 % de créances. C'est le plus permissif des standards "
            "implémentés sur ce poste."
        ),
    },
    "sc-malaisie": {
        "id": "sc-malaisie",
        "label": "SC Malaisie",
        "full": "Securities Commission Malaysia — Shariah Screening",
        "denominator": "total_assets",
        "denominator_label": "total du bilan",
        "denominator_complement": "au total du bilan",
        "ratios": {
            "debt": 0.33,
            "liquidity": 0.33,
        },
        "uses_receivables": False,
        "note": (
            "Le régulateur malaisien n'impose aucun seuil de créances : deux "
            "ratios seulement, rapportés au total du bilan. C'est le standard "
            "d'un pays où la finance islamique est la plus institutionnalisée, "
            "et il est plus simple que ceux des fournisseurs d'indices."
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
