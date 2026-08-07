"""
Ce qu'il faudrait pour qu'une valeur bascule.

Le calcul, et ce qu'il n'est pas
--------------------------------
On demande souvent à un screener de « prévoir » quand une action deviendra
conforme. C'est deux questions différentes, et une seule a une réponse
honnête.

**La question sans réponse** : *quand* ? Elle suppose de prédire soit le
cours de Bourse, soit la politique d'endettement d'une entreprise. Personne
ne sait faire ni l'un ni l'autre, et une date affichée avec assurance sur un
outil de screening religieux serait pire qu'inutile — quelqu'un achèterait
en s'y fiant.

**La question qui a une réponse exacte** : *à quelle condition* ? Elle ne
demande aucune prédiction, seulement une division. Les standards posent
`montant / dénominateur ≤ seuil` ; on connaît le montant et le seuil, on
résout pour le dénominateur.

  - Standards à **capitalisation boursière** (AAOIFI, Dow Jones, S&P) : le
    dénominateur est le cours multiplié par le nombre d'actions. On en
    déduit le cours exact au-delà duquel la valeur passe sous le seuil.
    C'est un fait vérifiable, pas un pronostic — et il dit aussi l'inverse :
    de combien le cours peut baisser avant qu'une valeur conforme cesse de
    l'être.

  - Standards au **total du bilan** (MSCI, FTSE, SC Malaisie) : le
    dénominateur ne dépend pas du marché. On calcule alors la dette maximale
    admissible, donc le désendettement nécessaire. Aucun cours n'y changera
    quoi que ce soit, et c'est une information en soi.

Nous affichons donc une condition, jamais une échéance.
"""

from screening import engine, standards


def _actions(societe):
    """Le nombre d'actions en circulation, déduit du dernier arrêté.

    On le reconstitue depuis la capitalisation et le cours plutôt que de
    lire `sharesOutstanding` : ces deux grandeurs viennent de la même
    photographie, alors que le champ de Yahoo peut dater d'un autre jour.
    """
    prix, cap = societe.get("prix"), societe.get("market_cap")
    if prix and cap and prix > 0:
        return cap / prix
    valo = societe.get("valorisation") or {}
    return valo.get("actions")


def conditions(societe, standard_id):
    """Les conditions de bascule, ratio par ratio.

    Renvoie une liste d'entrées décrivant, pour chaque ratio contraignant,
    ce qu'il faudrait pour passer de l'autre côté du seuil. Liste vide si
    le calcul n'a pas de sens — activité exclue, données manquantes.
    """
    std = standards.get(standard_id)
    resultat = engine.evaluate(societe, standard_id)

    # Une activité exclue ne bascule pas sur un ratio : aucune variation de
    # cours ne rend une banque conventionnelle conforme.
    if resultat.get("sector_verdict") == "exclu":
        return []

    entrees = []
    for ratio in resultat.get("ratios", []):
        if ratio.get("valeur") is None or not ratio.get("montant"):
            continue

        montant, seuil = ratio["montant"], ratio["seuil"]
        depasse = ratio["statut"] == "depasse"

        if std["denominator"] == "market_cap":
            actions = _actions(societe)
            if not actions:
                continue
            # montant / (cours × actions) = seuil  →  cours = montant / (seuil × actions)
            cours_pivot = montant / (seuil * actions)
            actuel = societe.get("prix")
            if not actuel:
                continue
            entrees.append({
                "ratio": ratio["label"],
                "type": "cours",
                "depasse": depasse,
                "pivot": cours_pivot,
                "actuel": actuel,
                "ecart": (cours_pivot - actuel) / actuel,
                "devise": societe.get("currency"),
            })
        else:
            total = societe.get("total_assets")
            if not total:
                continue
            # montant / total = seuil  →  montant admissible = seuil × total
            admissible = seuil * total
            entrees.append({
                "ratio": ratio["label"],
                "type": "montant",
                "depasse": depasse,
                "pivot": admissible,
                "actuel": montant,
                "ecart": (admissible - montant) / montant if montant else None,
                "devise": societe.get("currency"),
            })

    return entrees


def resume(societe, standard_id):
    """La condition la plus contraignante, celle qui décide du verdict.

    Sur une valeur non conforme, c'est le ratio qu'il faut redresser en
    premier ; sur une valeur conforme, c'est celui qui cédera en premier.
    """
    entrees = conditions(societe, standard_id)
    if not entrees:
        return None

    resultat = engine.evaluate(societe, standard_id)
    conforme = resultat["verdict"] == engine.CONFORME

    if conforme:
        # La marge la plus faible : le ratio le plus proche du seuil.
        return min(entrees, key=lambda e: abs(e.get("ecart") or 0))
    # Le dépassement le plus lourd : celui qui bloque.
    depasses = [e for e in entrees if e["depasse"]]
    if not depasses:
        return None
    return max(depasses, key=lambda e: abs(e.get("ecart") or 0))
