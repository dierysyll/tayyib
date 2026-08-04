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


def evaluate(company, standard_id=standards.DEFAULT_STANDARD):
    """Évalue une société selon un standard.

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
    denominateur = (
        company.get("market_cap")
        if std["denominator"] == "market_cap"
        else company.get("total_assets")
    )

    numerateurs = {
        "debt": company.get("total_debt"),
        "liquidity": company.get("cash_and_investments"),
        "receivables": company.get("receivables"),
    }

    depassement = False
    for cle, seuil in std["ratios"].items():
        valeur = _ratio(numerateurs.get(cle), denominateur)

        if valeur is None:
            resultat["donnees_manquantes"].append(standards.RATIO_LABELS[cle])
            statut = "inconnu"
        elif valeur > seuil:
            statut = "depasse"
            depassement = True
        else:
            statut = "ok"

        resultat["ratios"].append({
            "cle": cle,
            "label": standards.RATIO_LABELS[cle],
            "valeur": valeur,
            "seuil": seuil,
            "statut": statut,
            "montant": numerateurs.get(cle),
        })

    # --- 3. Verdict ------------------------------------------------------
    if depassement:
        depasses = [r["label"].lower() for r in resultat["ratios"] if r["statut"] == "depasse"]
        resultat["verdict"] = NON_CONFORME
        resultat["raison"] = (
            f"Seuil dépassé — {', '.join(depasses)} "
            f"(rapporté à la {std['denominator_label']})."
        )
    elif not denominateur:
        resultat["verdict"] = A_VERIFIER
        resultat["raison"] = (
            f"La {std['denominator_label']} est indisponible : aucun ratio "
            "n'a pu être calculé."
        )
    elif resultat["donnees_manquantes"]:
        resultat["verdict"] = A_VERIFIER
        resultat["raison"] = (
            "Donnée absente du bilan publié — "
            f"{', '.join(resultat['donnees_manquantes']).lower()}."
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


def purification(dividende, part_revenus_non_conformes):
    """Montant à purifier sur un dividende perçu.

    `part_revenus_non_conformes` est en pourcentage (2.4 pour 2,4 %), et
    doit venir du rapport annuel de la société : nous ne pouvons pas la
    deviner. C'est l'utilisateur qui la saisit.
    """
    if dividende is None or part_revenus_non_conformes is None:
        return None
    return dividende * (part_revenus_non_conformes / 100.0)
