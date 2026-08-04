"""
Le filtre sectoriel : l'activité de l'entreprise est-elle licite ?

Ce filtre passe AVANT les ratios financiers. Une banque conventionnelle
reste non conforme même avec un bilan impeccable — inutile de calculer.

Trois verdicts, et le troisième est le plus important :

  EXCLU     l'activité est non conforme, sans ambiguïté (alcool, tabac,
            jeux d'argent, banque et assurance conventionnelles…) ;
  A_VERIFIER l'intitulé sectoriel ne permet pas de trancher — c'est le cas
            de « Aerospace & Defense », qui mélange l'aviation civile
            (Airbus, Safran) et l'armement (Thales), ou de la restauration
            et l'hôtellerie, dont une partie du chiffre d'affaires vient de
            l'alcool ;
  OK        rien dans le secteur ne pose problème.

Le parti pris : ne jamais transformer une incertitude en verdict. Les
concurrents affichent « conforme » ou « non conforme » là où seul un
rapport annuel peut répondre. Un « à vérifier » honnête vaut mieux qu'un
« conforme » faux.

La classification sectorielle vient de Yahoo Finance (couple secteur /
industrie). Elle est grossière : c'est une raison de plus pour assumer la
catégorie intermédiaire.
"""

OK = "ok"
EXCLU = "exclu"
A_VERIFIER = "a_verifier"

# Industries non conformes, par mot-clé recherché dans l'intitulé Yahoo
# (en minuscules). L'ordre n'a pas d'importance : le premier motif trouvé
# suffit à exclure.
EXCLUDED_INDUSTRIES = {
    # Finance à intérêt
    "banks": "Banque conventionnelle — activité fondée sur l'intérêt (riba)",
    "credit services": "Crédit à la consommation — activité fondée sur l'intérêt (riba)",
    "mortgage": "Crédit hypothécaire — activité fondée sur l'intérêt (riba)",
    "capital markets": "Marchés de capitaux — activité fondée sur l'intérêt (riba)",
    "financial data": "Infrastructure de marché conventionnelle",
    "financial conglomerates": "Conglomérat financier conventionnel",
    "asset management": "Gestion d'actifs conventionnelle",
    "insurance": "Assurance conventionnelle — aléa (gharar) et intérêt (riba)",
    # Alcool et tabac
    "wineries": "Production d'alcool",
    "distilleries": "Production d'alcool",
    "brewers": "Production d'alcool",
    "tobacco": "Tabac",
    # Jeux d'argent
    "gambling": "Jeux d'argent (maysir)",
    "casino": "Jeux d'argent (maysir)",
    # Divertissement pour adultes
    "adult": "Contenu pour adultes",
}

# Industries qui demandent un examen du rapport annuel avant de trancher.
REVIEW_INDUSTRIES = {
    "aerospace & defense": (
        "Ce secteur mélange aviation civile et armement. Vérifier la part "
        "du chiffre d'affaires liée à l'armement."
    ),
    "restaurants": (
        "La restauration tire souvent une part de son chiffre d'affaires de "
        "l'alcool et du porc. Vérifier le détail du chiffre d'affaires."
    ),
    "lodging": (
        "L'hôtellerie tire souvent une part de son chiffre d'affaires de "
        "l'alcool. Vérifier le détail du chiffre d'affaires."
    ),
    "resorts": (
        "Les complexes hôteliers associent fréquemment jeux d'argent et "
        "alcool. Vérifier le détail du chiffre d'affaires."
    ),
    "entertainment": (
        "Le divertissement (cinéma, musique) fait l'objet d'appréciations "
        "divergentes selon les écoles. À trancher selon votre référence."
    ),
    "broadcasting": (
        "La diffusion audiovisuelle fait l'objet d'appréciations divergentes "
        "selon les écoles. À trancher selon votre référence."
    ),
    "beverages": (
        "Vérifier qu'il s'agit bien de boissons sans alcool."
    ),
    "rental & leasing": (
        "La location simple est licite (ijara) ; le crédit-bail assorti "
        "d'intérêts ne l'est pas. Vérifier la nature des contrats."
    ),
    "reit": (
        "Foncière cotée : vérifier l'activité des locataires, et noter que "
        "ces sociétés se financent massivement par dette portant intérêt."
    ),
    "food distribution": (
        "La grande distribution vend de l'alcool et du porc. Vérifier la "
        "part de ces rayons dans le chiffre d'affaires."
    ),
    "grocery stores": (
        "La grande distribution vend de l'alcool et du porc. Vérifier la "
        "part de ces rayons dans le chiffre d'affaires."
    ),
    "department stores": (
        "La distribution généraliste vend de l'alcool et du porc. Vérifier "
        "la part de ces rayons dans le chiffre d'affaires."
    ),
}


def screen(sector, industry):
    """Filtre sectoriel. Renvoie (verdict, motif).

    `sector` et `industry` sont les intitulés Yahoo Finance ; l'un ou
    l'autre peut être absent, auquel cas on ne peut pas trancher.
    """
    if not sector and not industry:
        return A_VERIFIER, "Secteur d'activité inconnu — impossible de trancher."

    haystack = f"{sector or ''} {industry or ''}".lower()

    for motif, raison in EXCLUDED_INDUSTRIES.items():
        if motif in haystack:
            return EXCLU, raison

    for motif, raison in REVIEW_INDUSTRIES.items():
        if motif in haystack:
            return A_VERIFIER, raison

    return OK, None
