"""
Le moteur : à partir des données d'une société et d'un standard, produire
un verdict motivé.

Trois verdicts possibles, et l'existence du troisième est un choix de
conception, pas une facilité :

  CONFORME     passe le filtre sectoriel et tous les ratios calculables ;
  NON_CONFORME activité exclue, ou au moins un ratio au-dessus du seuil ;
  A_VERIFIER   le secteur est ambigu, ou une donnée manque.

Ce que ce moteur ne fait pas, et ne fera jamais silencieusement
--------------------------------------------------------------
Les trois standards imposent un quatrième filtre : les revenus tirés
d'activités non conformes doivent rester sous 5 % du chiffre d'affaires.
Ce chiffre ne se déduit pas des données de marché — il se lit dans le
rapport annuel, ligne par ligne. Aucune source gratuite ne le publie.

Nous ne l'estimons pas, nous ne l'approximons pas, et nous ne le passons
pas sous silence : un verdict CONFORME est toujours accompagné de la
mention `revenue_filter_pending`, que l'interface affiche systématiquement.
« Conforme sur les critères calculables » est une phrase honnête ;
« conforme » tout court ne le serait pas.
"""

from screening import sectors, standards

CONFORME = "conforme"
NON_CONFORME = "non_conforme"
A_VERIFIER = "a_verifier"

VERDICT_LABELS = {
    CONFORME: "Conforme",
    NON_CONFORME: "Non conforme",
    A_VERIFIER: "À vérifier",
}


def _ratio(numerateur, denominateur):
    """Un ratio, ou None si le calcul n'a pas de sens. On refuse de diviser
    par zéro ou par un dénominateur absent plutôt que de renvoyer 0, qui
    serait lu comme « ratio excellent »."""
    if numerateur is None or not denominateur or denominateur <= 0:
        return None
    return numerateur / denominateur


def _denominateur(source, std):
    """Le dénominateur exigé par le standard, lu dans un jeu de données —
    société courante ou exercice passé, la structure est la même."""
    if std["denominator"] == "market_cap":
        return source.get("market_cap")
    return source.get("total_assets")


def _calcul_ratios(source, std):
    """Applique les ratios du standard à un jeu de données daté.

    Renvoie (ratios, depassement, manquants).
    """
    denominateur = _denominateur(source, std)
    numerateurs = {
        "debt": source.get("total_debt"),
        "liquidity": source.get("cash_and_investments"),
        "receivables": source.get("receivables"),
    }

    ratios, depassement, manquants = [], False, []
    for cle, seuil in std["ratios"].items():
        valeur = _ratio(numerateurs.get(cle), denominateur)

        if valeur is None:
            manquants.append(standards.RATIO_LABELS[cle])
            statut = "inconnu"
        elif valeur > seuil:
            statut = "depasse"
            depassement = True
        else:
            statut = "ok"

        ratios.append({
            "cle": cle,
            "label": standards.RATIO_LABELS[cle],
            "valeur": valeur,
            "seuil": seuil,
            "statut": statut,
            "montant": numerateurs.get(cle),
        })

    return ratios, depassement, manquants


def evaluate(company, standard_id=standards.DEFAULT_STANDARD):
    """Évalue une société selon un standard, sur son dernier exercice.

    `company` est le dictionnaire produit par data/yahoo.py.
    Renvoie un dictionnaire de résultat, prêt pour l'affichage.
    """
    std = standards.get(standard_id)

    resultat = {
        "standard": std,
        "verdict": None,
        "raison": None,
        "ratios": [],
        "sector_verdict": None,
        "sector_reason": None,
        "revenue_filter_pending": False,
        "donnees_manquantes": [],
    }

    # --- 1. Filtre sectoriel -------------------------------------------
    sector_verdict, sector_reason = sectors.screen(
        company.get("sector"), company.get("industry")
    )
    resultat["sector_verdict"] = sector_verdict
    resultat["sector_reason"] = sector_reason

    if sector_verdict == sectors.EXCLU:
        resultat["verdict"] = NON_CONFORME
        resultat["raison"] = sector_reason
        # On s'arrête là : les ratios d'une banque n'ont pas d'intérêt.
        return resultat

    # --- 2. Ratios financiers ------------------------------------------
    ratios, depassement, manquants = _calcul_ratios(company, std)
    resultat["ratios"] = ratios
    resultat["donnees_manquantes"] = manquants

    # --- 3. Verdict ------------------------------------------------------
    if depassement:
        depasses = [r["label"].lower() for r in ratios if r["statut"] == "depasse"]
        resultat["verdict"] = NON_CONFORME
        resultat["raison"] = (
            f"Seuil dépassé — {', '.join(depasses)} "
            f"(rapporté {std['denominator_complement']})."
        )
    elif not _denominateur(company, std):
        resultat["verdict"] = A_VERIFIER
        resultat["raison"] = (
            f"Dénominateur indisponible — {std['denominator_label']} : "
            "aucun ratio n'a pu être calculé."
        )
    elif manquants:
        resultat["verdict"] = A_VERIFIER
        resultat["raison"] = (
            "Donnée absente du bilan publié — "
            f"{', '.join(manquants).lower()}."
        )
    elif sector_verdict == sectors.A_VERIFIER:
        resultat["verdict"] = A_VERIFIER
        resultat["raison"] = sector_reason
    else:
        resultat["verdict"] = CONFORME
        resultat["raison"] = (
            "Activité licite et tous les ratios sous les seuils "
            f"{std['label']}."
        )

    # Le filtre des 5 % reste dû dès lors qu'on n'a pas déjà exclu la valeur.
    resultat["revenue_filter_pending"] = resultat["verdict"] != NON_CONFORME

    return resultat


def historique_conformite(company, standard_id=standards.DEFAULT_STANDARD):
    """Le verdict, exercice par exercice.

    Chaque exercice est jugé sur SES propres chiffres : dette, trésorerie
    et créances de l'arrêté, rapportées soit au total de bilan de l'arrêté,
    soit à la capitalisation reconstituée à cette date (cours de clôture ×
    nombre d'actions du même bilan — voir data/yahoo.py).

    Une limite, assumée et affichée : le **filtre sectoriel appliqué est
    celui d'aujourd'hui**. Yahoo ne publie pas l'activité historique d'une
    société, et une entreprise qui a cédé sa branche bancaire il y a trois
    ans apparaîtra donc exclue sur toute la période. C'est le sens
    conservateur, mais il faut le savoir pour lire la série.

    Renvoie la liste des exercices, du plus récent au plus ancien.
    """
    std = standards.get(standard_id)
    sector_verdict, sector_reason = sectors.screen(
        company.get("sector"), company.get("industry")
    )

    serie = []
    for periode in company.get("historique", []):
        entree = {
            "date": periode["date"],
            "annee": periode["date"][:4],
            "market_cap": periode.get("market_cap"),
            "cours": periode.get("cours"),
            "revenu": periode.get("revenu"),
            "resultat_net": periode.get("resultat_net"),
            "ratios": [],
            "verdict": None,
        }

        if sector_verdict == sectors.EXCLU:
            entree["verdict"] = NON_CONFORME
            entree["raison"] = sector_reason
            serie.append(entree)
            continue

        ratios, depassement, manquants = _calcul_ratios(periode, std)
        entree["ratios"] = ratios

        if depassement:
            entree["verdict"] = NON_CONFORME
        elif not _denominateur(periode, std) or manquants:
            entree["verdict"] = A_VERIFIER
        elif sector_verdict == sectors.A_VERIFIER:
            entree["verdict"] = A_VERIFIER
        else:
            entree["verdict"] = CONFORME

        serie.append(entree)

    return serie


def purification(dividende, part_revenus_non_conformes):
    """Montant à purifier sur un dividende perçu.

    `part_revenus_non_conformes` est en pourcentage (2.4 pour 2,4 %), et
    doit venir du rapport annuel de la société : nous ne pouvons pas la
    deviner. C'est l'utilisateur qui la saisit.
    """
    if dividende is None or part_revenus_non_conformes is None:
        return None
    return dividende * (part_revenus_non_conformes / 100.0)
