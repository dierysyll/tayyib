"""
Les analyses : ce que le screening produit une fois qu'on le regarde à
l'échelle de l'univers entier, et non valeur par valeur.

Un screener répond à « cette action est-elle conforme ? ». C'est utile,
mais c'est aussi ce que font tous les autres. Les questions auxquelles
personne ne répond pour un investisseur musulman sont ailleurs :

  - **Qu'est-ce qui a changé ?** Une société qui se désendette redevient
    conforme, une société qui rachète ses actions à crédit cesse de
    l'être. Ce basculement, personne ne le publie — alors qu'il oblige à
    vendre, ou autorise à acheter.
  - **Où sont les valeurs conformes qui rapportent ?** Filtrer, c'est
    retirer ; un investisseur veut aussi une liste courte à examiner.
  - **Où le monde est-il investissable ?** Le taux de conformité par place
    dit quelque chose de vrai sur les économies : Riyad n'a pas la même
    structure financière que Francfort.
  - **Les standards sont-ils d'accord ?** Quand ils divergent sur une
    valeur, c'est le signal qu'il faut lire le détail plutôt que le
    verdict.

Tout ici se calcule à partir du cache : aucune source supplémentaire,
aucune opinion ajoutée.
"""

from screening import engine, standards


def _rendement(valeur):
    """Le rendement du dividende, converti en fraction.

    Yahoo exprime `dividendYield` en **pourcentage**, toujours : 0,47 pour
    Nvidia signifie 0,47 %, et non 47 %.

    Une version antérieure de ce code croyait le champ ambigu et tranchait
    sur l'ordre de grandeur — « au-dessus de 1, c'est déjà un pourcentage ;
    en dessous, c'est une fraction ». L'heuristique passait inaperçue tant
    que l'univers se limitait à Paris, où presque toutes les valeurs
    rendent plus de 1 %. Étendue aux valeurs de croissance américaines,
    elle affichait Microsoft à 78 % de rendement.

    Vérification faite sur l'univers collecté, en recoupant le champ avec
    le dividende par action rapporté au cours : 753 valeurs concordent avec
    la lecture « pourcentage », contre 70 écarts, tous situés à Koweït où
    la source mélange elle-même ses unités de cotation.
    """
    brut = valeur.get("rendement")
    if not brut:
        return None
    return brut / 100.0


def changements(valeurs, standard_id):
    """Les valeurs dont le verdict a basculé au dernier arrêté comptable.

    On compare le verdict de l'exercice le plus récent à celui de
    l'exercice précédent, tous deux calculés sur leurs propres chiffres
    (voir engine.historique_conformite). Une entrée en conformité est une
    occasion ; une sortie est une obligation d'arbitrer.

    Limite assumée, la même que pour l'historique : le filtre sectoriel
    appliqué aux deux exercices est celui d'aujourd'hui. Un basculement
    signalé ici vient donc toujours des ratios, jamais d'un changement
    d'activité — ce qui est précisément ce qu'on veut suivre.
    """
    entrees, sorties = [], []

    for valeur in valeurs:
        serie = engine.historique_conformite(valeur, standard_id)
        if len(serie) < 2:
            continue

        recent, precedent = serie[0], serie[1]
        if recent["verdict"] == precedent["verdict"]:
            continue

        mouvement = {
            "societe": valeur,
            "avant": precedent["verdict"],
            "apres": recent["verdict"],
            "date": recent["date"],
            "annee_avant": precedent["annee"],
            "annee_apres": recent["annee"],
        }

        if recent["verdict"] == engine.CONFORME:
            entrees.append(mouvement)
        elif precedent["verdict"] == engine.CONFORME:
            sorties.append(mouvement)

    cle = lambda m: -(m["societe"].get("market_cap_eur") or 0)
    return sorted(entrees, key=cle), sorted(sorties, key=cle)


def palmares_rendement(evaluees, limite=12):
    """Les valeurs conformes qui versent le plus, par rendement décroissant.

    Réservé aux conformes : proposer un classement de rendement où
    figureraient des valeurs exclues serait une invitation contradictoire.
    """
    candidates = [
        {"societe": e["societe"], "rendement": _rendement(e["societe"])}
        for e in evaluees
        if e["resultat"]["verdict"] == engine.CONFORME and _rendement(e["societe"])
    ]
    return sorted(candidates, key=lambda c: -c["rendement"])[:limite]


def palmares_taille(evaluees, limite=12):
    """Les plus grosses valeurs conformes, en euros convertis."""
    candidates = [
        e for e in evaluees
        if e["resultat"]["verdict"] == engine.CONFORME
        and e["societe"].get("market_cap_eur")
    ]
    return sorted(candidates, key=lambda e: -e["societe"]["market_cap_eur"])[:limite]


def par_place(evaluees, places):
    """Le taux de conformité place par place.

    Une lecture à prendre avec précaution, et l'interface le dit : un taux
    bas peut refléter la structure d'une économie (Francfort compte
    beaucoup de banques) autant qu'une lacune de nos données (Le Caire ne
    renseigne pas les secteurs, donc tout y tombe en « à vérifier »).
    """
    compteurs = {}
    for e in evaluees:
        place_id = e["societe"].get("place")
        if not place_id or place_id not in places:
            continue
        case = compteurs.setdefault(place_id, {
            "place": dict(places[place_id], id=place_id),
            "total": 0,
            engine.CONFORME: 0,
            engine.A_VERIFIER: 0,
            engine.NON_CONFORME: 0,
        })
        case["total"] += 1
        case[e["resultat"]["verdict"]] += 1

    lignes = []
    for case in compteurs.values():
        case["part_conforme"] = case[engine.CONFORME] / case["total"] if case["total"] else 0
        lignes.append(case)

    return sorted(lignes, key=lambda c: -c["part_conforme"])


def desaccords(valeurs, limite=14):
    """Les valeurs sur lesquelles les trois standards ne s'accordent pas.

    C'est l'illustration la plus concrète du fait que « halal » n'est pas
    une propriété de l'entreprise mais le résultat d'une convention de
    calcul : même société, même jour, verdicts opposés selon qu'on
    rapporte la dette à la capitalisation ou au total du bilan.
    """
    lignes = []
    for valeur in valeurs:
        verdicts = {
            sid: engine.evaluate(valeur, sid)["verdict"]
            for sid in standards.STANDARDS
        }
        if len(set(verdicts.values())) < 2:
            continue
        # On ne retient que les désaccords tranchés : un « à vérifier »
        # face à un « conforme » est un doute, pas une contradiction.
        if engine.CONFORME in verdicts.values() and engine.NON_CONFORME in verdicts.values():
            lignes.append({
                "societe": valeur,
                "verdicts": verdicts,
                "taille": valeur.get("market_cap_eur") or 0,
            })

    return sorted(lignes, key=lambda l: -l["taille"])[:limite]


def repartition_standards(valeurs):
    """La répartition des verdicts pour chacun des trois standards.

    Le tableau que le lecteur doit voir avant de choisir : les écarts
    entre standards ne sont pas marginaux, ils portent sur des dizaines de
    pourcents de l'univers.
    """
    lignes = []
    for sid, std in standards.STANDARDS.items():
        compte = {engine.CONFORME: 0, engine.A_VERIFIER: 0, engine.NON_CONFORME: 0}
        for valeur in valeurs:
            compte[engine.evaluate(valeur, sid)["verdict"]] += 1
        total = sum(compte.values()) or 1
        lignes.append({
            "standard": std,
            "compte": compte,
            "part": {v: n / total for v, n in compte.items()},
            "total": total,
        })
    return lignes


def secteurs_conformes(evaluees, limite=10):
    """Les secteurs où l'on trouve le plus de valeurs conformes.

    Utile pour orienter une recherche : c'est une carte des zones de
    l'économie compatibles avec un portefeuille conforme.
    """
    compteurs = {}
    for e in evaluees:
        secteur = e["societe"].get("sector")
        if not secteur:
            continue
        case = compteurs.setdefault(secteur, {"secteur": secteur, "total": 0, "conformes": 0})
        case["total"] += 1
        if e["resultat"]["verdict"] == engine.CONFORME:
            case["conformes"] += 1

    lignes = [c for c in compteurs.values() if c["conformes"]]
    for ligne in lignes:
        ligne["part"] = ligne["conformes"] / ligne["total"]
    return sorted(lignes, key=lambda c: -c["conformes"])[:limite]
