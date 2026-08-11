"""
Tayyib — le screener boursier halal, en français, pour le monde entier.

Le nom vient de « halalan tayyiban » : licite, et pur.

L'application est volontairement mince. Toute la matière est dans
screening/ (les règles et les analyses), data/ (la collecte) et charts.py
(la projection SVG) ; ici on ne fait que router, filtrer, trier et rendre.
"""

import os
import threading
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from flask import Flask, abort, jsonify, render_template, request

import charts
from data import cache, fx, presse, universe, yahoo
from screening import (alias, analyses, bascule, engine, notation, standards,
                       vocabulaire)

app = Flask(__name__)


def _langue():
    """La langue d'affichage : celle demandée dans l'URL, sinon celle
    retenue au passage précédent, sinon le français."""
    demandee = request.args.get("lang")
    if demandee in vocabulaire.LANGUES:
        return demandee
    return vocabulaire.normalise(request.cookies.get("lang", ""))


@app.context_processor
def _injecte_langue():
    langue = _langue()
    return {
        "lang": langue,
        "langues": vocabulaire.LANGUES,
        "secteur_fr": lambda nom: vocabulaire.secteur(nom, langue),
        "activite": lambda societe: vocabulaire.activite(societe, langue),
    }


@app.after_request
def _memorise_langue(reponse):
    """Mémorise la langue choisie explicitement, pour que la navigation
    suivante la conserve sans réécrire toutes les URL."""
    demandee = request.args.get("lang", "")
    if demandee in vocabulaire.LANGUES and request.cookies.get("lang") != demandee:
        reponse.set_cookie("lang", demandee, max_age=60 * 60 * 24 * 365,
                           samesite="Lax")
    return reponse

# Ordre d'affichage : ce qu'on peut acheter d'abord, ce qui est exclu en
# dernier. Un screener sert à trouver, pas à parcourir des rejets.
ORDRE_VERDICT = {
    engine.CONFORME: 0,
    engine.A_VERIFIER: 1,
    engine.NON_CONFORME: 2,
}

TRIS = {
    "pertinence": "Conformité",
    "capitalisation": "Capitalisation",
    "nom": "Nom",
    "rendement": "Rendement",
}

# Au-delà, la page devient interminable et le navigateur peine. L'univers
# entier reste accessible : c'est le filtrage qui sert à le parcourir.
PAR_PAGE = 120


def _univers(standard_id):
    """L'univers évalué selon un standard, avec la date de collecte."""
    valeurs, fetched_at, taux = cache.index()
    evaluees = []
    for s in valeurs:
        resultat = engine.evaluate(s, standard_id)
        evaluees.append({
            "societe": s,
            "resultat": resultat,
            "note": notation.note(resultat),
        })
    return evaluees, fetched_at, taux


def _trier(evaluees, tri):
    if tri == "nom":
        return sorted(evaluees, key=lambda e: (e["societe"].get("nom") or "").lower())
    if tri == "capitalisation":
        # En euros convertis : sans cela, une capitalisation en roupies
        # indonésiennes écraserait tout le classement (voir data/fx.py).
        return sorted(evaluees, key=lambda e: -(e["societe"].get("market_cap_eur") or 0))
    if tri == "rendement":
        return sorted(evaluees, key=lambda e: -(analyses._rendement(e["societe"]) or 0))
    # Par défaut : les valeurs investissables d'abord, puis les plus grosses.
    return sorted(evaluees, key=lambda e: (
        ORDRE_VERDICT[e["resultat"]["verdict"]],
        -(e["societe"].get("market_cap_eur") or 0),
    ))


def _standard_demande():
    return request.args.get("standard", standards.DEFAULT_STANDARD)


def _filtrer_geographie(evaluees, region, place):
    """Restreint l'univers à une région ou à une place."""
    if place and place in universe.PLACES:
        return [e for e in evaluees if e["societe"].get("place") == place]
    if region and region in universe.REGIONS:
        places = {pid for pid, p in universe.PLACES.items() if p["region"] == region}
        return [e for e in evaluees if e["societe"].get("place") in places]
    return evaluees


@app.route("/")
def accueil():
    standard_id = _standard_demande()
    tous, fetched_at, _ = _univers(standard_id)

    region = request.args.get("region") or None
    place = request.args.get("place") or None
    # La portée géographique s'applique avant tout le reste : les compteurs
    # doivent décrire le périmètre choisi, pas l'univers entier.
    portee = _filtrer_geographie(tous, region, place)

    evaluees = portee
    q = (request.args.get("q") or "").strip()
    if q:
        terme = q.lower()
        evaluees = [
            e for e in evaluees
            if terme in (e["societe"].get("nom") or "").lower()
            or terme in (e["societe"].get("ticker") or "").lower()
        ]

    filtre = request.args.get("verdict")
    if filtre in ORDRE_VERDICT:
        evaluees = [e for e in evaluees if e["resultat"]["verdict"] == filtre]

    secteur = request.args.get("secteur")
    if secteur:
        evaluees = [e for e in evaluees if e["societe"].get("sector") == secteur]

    tri = request.args.get("tri", "pertinence")
    evaluees = _trier(evaluees, tri)

    total_filtre = len(evaluees)
    tronque = total_filtre > PAR_PAGE
    evaluees = evaluees[:PAR_PAGE]

    compteurs = {
        v: sum(1 for e in portee if e["resultat"]["verdict"] == v)
        for v in ORDRE_VERDICT
    }

    # Triés sur le libellé affiché, pas sur l'intitulé Yahoo : en français,
    # « Énergie » ne se range pas où se rangeait « Energy ».
    langue = _langue()
    secteurs = sorted(
        {e["societe"]["sector"] for e in portee if e["societe"].get("sector")},
        key=lambda s: vocabulaire.secteur(s, langue).lower(),
    )

    # Bandeau et palmarès : ils portent sur le périmètre choisi, pour qu'un
    # lecteur qui a filtré sur Riyad ne voie pas défiler des valeurs de Paris.
    mobiles = [e for e in portee if e["societe"].get("variation") is not None]
    par_variation = sorted(mobiles, key=lambda e: -e["societe"]["variation"])

    return render_template(
        "index.html",
        evaluees=evaluees,
        bandeau=_trier(
            [e for e in portee if e["societe"].get("variation") is not None],
            "capitalisation",
        )[:26],
        hausses=par_variation[:6],
        baisses=list(reversed(par_variation[-6:])),
        compteurs=compteurs,
        total=len(portee),
        total_univers=len(tous),
        total_filtre=total_filtre,
        tronque=tronque,
        par_page=PAR_PAGE,
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
        fetched_at=fetched_at,
        q=q,
        filtre=filtre,
        secteur=secteur,
        secteurs=secteurs,
        tri=tri,
        tris=TRIS,
        region=region,
        place=place,
        regions=_regions_comptees(tous),
        places=_places_comptees(tous, region),
        toutes_places=universe.PLACES,
        engine=engine,
    )


def _regions_comptees(evaluees):
    """Les régions, avec le nombre de valeurs réellement collectées."""
    comptes = {}
    for e in evaluees:
        place = universe.PLACES.get(e["societe"].get("place"))
        if place:
            comptes[place["region"]] = comptes.get(place["region"], 0) + 1
    return [
        dict(region, compte=comptes.get(rid, 0))
        for rid, region in universe.REGIONS.items()
        if comptes.get(rid)
    ]


def _places_comptees(evaluees, region):
    """Les places de la région choisie. Sans région, on ne propose rien :
    vingt-neuf pastilles d'un coup ne sont pas un filtre, c'est un mur."""
    if not region or region not in universe.REGIONS:
        return []
    comptes = {}
    for e in evaluees:
        pid = e["societe"].get("place")
        if pid:
            comptes[pid] = comptes.get(pid, 0) + 1
    return [
        dict(place, id=pid, compte=comptes.get(pid, 0))
        for pid, place in universe.PLACES.items()
        if place["region"] == region and comptes.get(pid)
    ]


@app.route("/valeur/<ticker>")
def valeur(ticker):
    standard_id = _standard_demande()
    valeurs, fetched_at, _ = cache.index()

    resume = next(
        (v for v in valeurs if (v.get("ticker") or "").lower() == ticker.lower()),
        None,
    )
    if resume is None:
        abort(404)

    # Le détail — historique de cours, comptes, dividendes — vit dans un
    # fichier séparé, lu seulement ici (voir data/cache.py).
    societe = cache.detail(resume["ticker"]) or resume

    resultat = engine.evaluate(societe, standard_id)
    historique = engine.historique_conformite(societe, standard_id)

    # Le même titre selon les trois standards : c'est souvent là que le
    # lecteur comprend que « halal » n'est pas une propriété binaire de
    # l'entreprise, mais le résultat d'une convention de calcul.
    comparaison = [
        {"standard": std, "resultat": engine.evaluate(societe, sid)}
        for sid, std in standards.STANDARDS.items()
    ]

    graphique = charts.courbe_cours(
        societe.get("cours"),
        jalons=[{"date": h["date"], "verdict": h["verdict"]} for h in historique],
    )

    # Le verdict affiché rapporte le dernier bilan à la capitalisation du
    # JOUR ; l'historique rapporte ce même bilan à la capitalisation de la
    # date d'arrêté. Quand les deux divergent, c'est le cours qui a bougé,
    # et le lecteur doit le savoir : sa conformité est réversible.
    bascule_cours = None
    std = standards.get(standard_id)
    if historique and std["denominator"] == "market_cap":
        recent = historique[0]
        if recent["verdict"] != resultat["verdict"]:
            bascule_cours = {
                "verdict_arrete": recent["verdict"],
                "date": recent["date"],
                "cours_arrete": recent.get("cours"),
                "cours_actuel": societe.get("prix"),
            }

    # Les dépêches déjà collectées pour cette valeur. Les autres sont
    # chargées à la demande par l'onglet Actualités.
    depeches, _ = cache.actus()
    depeches = [a for a in depeches if a.get("ticker") == societe["ticker"]]

    return render_template(
        "valeur.html",
        bascule_cours=bascule_cours,
        note=notation.note(resultat),
        condition=bascule.resume(societe, standard_id),
        depeches=depeches,
        societe=societe,
        place=universe.PLACES.get(societe.get("place")),
        resultat=resultat,
        historique=historique,
        graphique=graphique,
        comparaison=comparaison,
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
        fetched_at=fetched_at,
        engine=engine,
    )


@app.route("/analyses", endpoint="analyses")
def analyses_page():
    standard_id = _standard_demande()
    evaluees, fetched_at, _ = _univers(standard_id)
    valeurs = [e["societe"] for e in evaluees]

    entrees, sorties = analyses.changements(valeurs, standard_id)

    # Le compte des verdicts, pour les compteurs de tête. La page l'énonçait
    # jusqu'ici en prose au fil des sections ; un lecteur qui arrive veut
    # d'abord savoir de combien de valeurs on parle, et combien passent.
    compte = {"conforme": 0, "a_verifier": 0, "non_conforme": 0}
    for e in evaluees:
        compte[e["resultat"]["verdict"]] += 1

    return render_template(
        "analyses.html",
        entrees=entrees[:12],
        sorties=sorties[:12],
        nb_entrees=len(entrees),
        nb_sorties=len(sorties),
        compte=compte,
        rendements=analyses.palmares_rendement(evaluees),
        tailles=analyses.palmares_taille(evaluees),
        places=analyses.par_place(evaluees, universe.PLACES),
        desaccords=analyses.desaccords(valeurs),
        repartitions=analyses.repartition_standards(valeurs),
        secteurs=analyses.secteurs_conformes(evaluees),
        total=len(valeurs),
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
        fetched_at=fetched_at,
        engine=engine,
    )


# --- Fraîcheur du fil de presse -----------------------------------------
#
# Les cours et les bilans se collectent hors ligne : ils changent lentement,
# et interroger Yahoo mille fois par visite serait absurde. La presse, non.
# Un fil d'actualité qui date de la dernière commande lancée à la main n'est
# pas un fil d'actualité.
#
# Onze flux RSS coûtent quelques secondes — trop pour les faire attendre au
# visiteur, assez peu pour les rafraîchir en tâche de fond dès que le cache
# a vieilli. Celui qui arrive lit la version précédente ; le suivant a la
# nouvelle.

PRESSE_FRAICHEUR = timedelta(minutes=30)
_presse_en_cours = threading.Lock()


def _rafraichir_presse_si_besoin():
    _, collecte = cache.presse()
    if collecte and datetime.now(timezone.utc) - collecte < PRESSE_FRAICHEUR:
        return
    # `acquire(blocking=False)` : si un rafraîchissement tourne déjà, on
    # laisse tomber plutôt que d'en empiler un par visiteur.
    if not _presse_en_cours.acquire(blocking=False):
        return

    def travail():
        try:
            articles = presse.collecte()
            if articles:
                cache.save_presse(articles)
        except Exception:
            # Un flux qui tombe ne doit pas faire tomber la page : on garde
            # la version précédente et on réessaiera au prochain passage.
            pass
        finally:
            _presse_en_cours.release()

    threading.Thread(target=travail, daemon=True).start()


@app.route("/actualites")
def actualites():
    """Deux fils, volontairement distincts.

    Le fil de presse francophone (marchés, Afrique, monde musulman) est
    celui qui parle au lecteur ; les dépêches Yahoo, anglophones, ont pour
    seul mérite d'être rattachées à une valeur précise et à son verdict.
    Les mélanger produirait une bouillie où l'on ne saurait plus ce qu'on
    lit — on les sépare donc en rubriques.
    """
    standard_id = _standard_demande()
    rubrique = request.args.get("rubrique", "marches")

    _rafraichir_presse_si_besoin()
    articles_presse, collecte_presse = cache.presse()
    depeches, collecte_yahoo = cache.actus()

    if rubrique == "valeurs":
        valeurs, _, _ = cache.index()
        index_valeurs = {v["ticker"]: v for v in valeurs}
        articles = []
        for depeche in depeches:
            societe = index_valeurs.get(depeche.get("ticker"))
            if not societe:
                continue
            articles.append({
                **depeche,
                "societe": societe,
                "verdict": engine.evaluate(societe, standard_id)["verdict"],
                "place": universe.PLACES.get(societe.get("place")),
            })

        filtre = request.args.get("verdict")
        if filtre in ORDRE_VERDICT:
            articles = [a for a in articles if a["verdict"] == filtre]
        collecte = collecte_yahoo
    else:
        if rubrique not in presse.RUBRIQUES:
            rubrique = "marches"
        articles = [a for a in articles_presse if a.get("rubrique") == rubrique]
        filtre = None
        collecte = collecte_presse

    comptes = {
        rid: sum(1 for a in articles_presse if a.get("rubrique") == rid)
        for rid in presse.RUBRIQUES
    }
    comptes["valeurs"] = len(depeches)

    return render_template(
        "actualites.html",
        articles=articles[:48],
        rubrique=rubrique,
        rubriques=presse.RUBRIQUES,
        comptes=comptes,
        filtre=filtre,
        collecte=collecte,
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
        engine=engine,
    )


@app.route("/place/<place_id>")
def place(place_id):
    """La fiche d'une place de marché.

    Une pastille qui ne fait que filtrer laisse le lecteur sans réponse à
    la question qu'il se pose vraiment en cliquant : qu'est-ce que cette
    place, et pourquoi y trouve-t-on si peu — ou si beaucoup — de valeurs
    conformes ?
    """
    infos = universe.PLACES.get(place_id)
    if infos is None:
        abort(404)

    standard_id = _standard_demande()
    evaluees, fetched_at, _ = _univers(standard_id)
    sur_place = [e for e in evaluees if e["societe"].get("place") == place_id]

    compteurs = {
        v: sum(1 for e in sur_place if e["resultat"]["verdict"] == v)
        for v in ORDRE_VERDICT
    }

    # Le même exercice selon les six standards : c'est sur une place entière
    # que l'écart entre conventions devient parlant.
    par_standard = [
        {
            "standard": std,
            "conformes": sum(
                1 for e in sur_place
                if engine.evaluate(e["societe"], sid)["verdict"] == engine.CONFORME
            ),
        }
        for sid, std in standards.STANDARDS.items()
    ]

    # Toutes les places ne publient pas de capitalisation : celles que nous
    # collectons nous-mêmes n'en ont pas encore.
    avec_capi = any(e["societe"].get("market_cap_eur") for e in sur_place)

    langue = _langue()
    secteurs = {}
    for e in sur_place:
        nom = vocabulaire.secteur(e["societe"].get("sector"), langue)
        if not nom:
            continue
        case = secteurs.setdefault(nom, {"nom": nom, "total": 0, "conformes": 0})
        case["total"] += 1
        if e["resultat"]["verdict"] == engine.CONFORME:
            case["conformes"] += 1

    return render_template(
        "place.html",
        place=dict(infos, id=place_id),
        region=universe.REGIONS[infos["region"]],
        compteurs=compteurs,
        total=len(sur_place),
        declarees=len(infos["valeurs"]),
        par_standard=par_standard,
        secteurs=sorted(secteurs.values(), key=lambda s: -s["total"]),
        # Sur une place sans capitalisation publiée — la BRVM aujourd'hui —
        # trier par taille revient à ne pas trier du tout, et la page
        # s'ouvrait sur quatre banques exclues. On retombe alors sur l'ordre
        # par conformité : un screener sert à trouver, pas à parcourir des
        # rejets.
        vedettes=_trier(sur_place, "capitalisation" if avec_capi else "pertinence")[:12],
        avec_capi=avec_capi,
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
        fetched_at=fetched_at,
        engine=engine,
    )


@app.route("/api/recherche.json")
def api_recherche():
    """L'index de la recherche globale.

    Un seul appel, mis en cache par le navigateur : valeurs, places,
    secteurs et pages dans une même liste, que le client filtre lui-même.
    Chercher ne doit pas coûter un aller-retour réseau par frappe.
    """
    langue = _langue()
    valeurs, _, _ = cache.index()
    standard_id = _standard_demande()

    # Les clés sont dépouillées de leurs accents et enrichies des noms
    # usuels : personne ne cherche « Saudi Arabian Oil Company », et
    # personne ne tape l'accent grave de « Hermès ».
    entrees = [
        {
            "type": "valeur",
            "libelle": v["nom"],
            "detail": f'{v["ticker"]} · {vocabulaire.activite(v, langue) or ""}'.strip(" ·"),
            "url": f'/valeur/{v["ticker"]}?standard={standard_id}',
            "cle": alias.cle_recherche(v),
            "poids": v.get("market_cap_eur") or 0,
        }
        for v in valeurs
    ]

    entrees += [
        {
            "type": "place",
            "libelle": p["nom"],
            "detail": f'{p["code"]} · {p["pays"]} · {p["indice"]}',
            "url": f'/place/{pid}?standard={standard_id}',
            "cle": alias.sans_accents(f'{p["nom"]} {p["pays"]} {p["indice"]} {p["devise"]}'),
            "poids": 1e12,
        }
        for pid, p in universe.PLACES.items()
    ]

    secteurs = sorted({v["sector"] for v in valeurs if v.get("sector")})
    entrees += [
        {
            "type": "secteur",
            "libelle": vocabulaire.secteur(s, langue),
            "detail": "Secteur d'activité",
            "url": f"/?standard={standard_id}&secteur={quote(s)}",
            "cle": alias.sans_accents(f"{vocabulaire.secteur(s, langue)} {s}"),
            "poids": 5e11,
        }
        for s in secteurs
    ]

    entrees += [
        {"type": "page", "libelle": libelle, "detail": detail, "url": url,
         "cle": alias.sans_accents(f"{libelle} {detail}"), "poids": 9e11}
        for libelle, detail, url in [
            ("Screener", "Filtrer l'univers", "/"),
            ("Analyses", "Basculements, palmarès, désaccords", "/analyses"),
            ("Actualités", "Presse francophone et monde musulman", "/actualites"),
            ("Portefeuille", "Vos lignes, en local", "/portefeuille"),
            ("Purification", "Montant à purifier sur les dividendes", "/purification"),
            ("Zakat", "Assiette, nissab, 2,5 %", "/zakat"),
            ("Méthodologie", "Comment les verdicts sont produits", "/methodologie"),
        ]
    ]

    return jsonify({"entrees": entrees})


@app.route("/api/cours/<ticker>.json")
def api_cours(ticker):
    """L'historique de cours d'une valeur, en pas journalier.

    La collecte de masse stocke un point par semaine sur six ans : assez
    pour situer les arrêtés comptables, beaucoup trop grossier pour lire un
    mois. Le pas journalier est donc récupéré ici, à la demande et pour une
    seule valeur, puis conservé sur disque — un visiteur le paie une fois,
    les suivants jamais.
    """
    valeurs, _, _ = cache.index()
    connu = next(
        (v for v in valeurs if (v.get("ticker") or "").lower() == ticker.lower()),
        None,
    )
    if connu is None:
        abort(404)

    # Les places que nous collectons nous-mêmes ne sont pas chez Yahoo :
    # l'y chercher échouerait à chaque ouverture de fiche, et la série que
    # nous archivons jour après jour est déjà dans le détail.
    if universe.PLACES.get(connu.get("place"), {}).get("source"):
        points = None
    else:
        points = cache.cours_journalier(connu["ticker"])
        if points is None:
            points = yahoo.fetch_cours_journalier(connu["ticker"])
            if points:
                cache.save_cours_journalier(connu["ticker"], points)

    detail = cache.detail(connu["ticker"]) or {}
    return jsonify({
        "ticker": connu["ticker"],
        "devise": connu.get("currency"),
        "journalier": points or [],
        "hebdomadaire": detail.get("cours") or [],
    })


@app.route("/portefeuille")
def portefeuille():
    """Analyse de portefeuille.

    Aucun compte, aucune inscription : les lignes vivent dans le
    navigateur (localStorage). C'est un choix délibéré — un screener n'a
    pas besoin de savoir ce que ses visiteurs détiennent, et ne pas
    collecter une donnée reste la seule façon certaine de ne pas la
    perdre.
    """
    standard_id = _standard_demande()
    return render_template(
        "portefeuille.html",
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
    )


@app.route("/suivi")
def suivi():
    """Les valeurs qu'on surveille, et ce qu'il faudrait pour qu'elles
    basculent.

    Comme le portefeuille, la liste vit dans le navigateur : surveiller une
    valeur n'est pas une information que ce site a besoin de détenir.
    """
    standard_id = _standard_demande()
    return render_template(
        "suivi.html",
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
    )


@app.route("/api/bascule.json")
def api_bascule():
    """Conditions de bascule et verdicts, pour la page de suivi.

    Un seul appel pour toute la liste : la page est consultée pour
    comparer plusieurs valeurs, pas une seule.
    """
    standard_id = _standard_demande()
    demandes = [t for t in (request.args.get("tickers") or "").split(",") if t]
    valeurs, _, _ = cache.index()
    index_valeurs = {v["ticker"]: v for v in valeurs}

    reponse = []
    for ticker in demandes[:60]:
        societe = index_valeurs.get(ticker)
        if not societe:
            continue
        resultat = engine.evaluate(societe, standard_id)
        reponse.append({
            "ticker": ticker,
            "nom": societe["nom"],
            "place": societe.get("place"),
            "prix": societe.get("prix"),
            "devise": societe.get("currency"),
            "variation": societe.get("variation"),
            "verdict": resultat["verdict"],
            "raison": resultat["raison"],
            "note": notation.note(resultat),
            "condition": bascule.resume(societe, standard_id),
        })
    return jsonify({"standard": standards.get(standard_id)["label"], "valeurs": reponse})


@app.route("/outils")
def outils():
    """Les calculateurs de projection patrimoniale.

    Tout est calculé dans le navigateur : ces outils ne consultent aucune
    donnée personnelle et n'en transmettent aucune. Les taux de change
    viennent de la collecte, le reste est de l'arithmétique.
    """
    _, _, taux = cache.index()
    devises = [d for d in fx.DEVISES_USUELLES if d["code"] in taux]
    return render_template(
        "outils.html",
        devises=devises,
        taux={d["code"]: taux[d["code"]] for d in devises},
        metaux=cache.metaux(),
        standard=standards.get(_standard_demande()),
        standards=standards.STANDARDS,
    )


@app.route("/purification")
def purification():
    """Le calcul du montant à purifier sur les dividendes perçus."""
    standard_id = _standard_demande()
    return render_template(
        "purification.html",
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
        seuil=standards.NON_COMPLIANT_INCOME_MAX,
    )


@app.route("/zakat")
def zakat():
    """La zakat sur un patrimoine.

    Volontairement pas « sur un portefeuille d'actions » : la zakat porte
    sur ce qu'on possède, et beaucoup de musulmans francophones n'ont pas
    d'actions du tout. Quelqu'un à Dakar ou à Casablanca compte son épargne
    en francs CFA ou en dirhams — la page doit savoir les additionner.
    """
    _, _, taux = cache.index()
    # On n'expose que les devises dont on a réellement le taux : proposer
    # une devise puis afficher « — » à la place du montant serait pire que
    # de ne pas la proposer.
    devises = [d for d in fx.DEVISES_USUELLES if d["code"] in taux]
    return render_template(
        "zakat.html",
        metaux=cache.metaux(),
        devises=devises,
        taux={d["code"]: taux[d["code"]] for d in devises},
        standard=standards.get(_standard_demande()),
        standards=standards.STANDARDS,
    )


@app.route("/api/univers.json")
def api_univers():
    """Univers compact, pour les pages portefeuille, purification et zakat.

    Les montants sont exposés deux fois : dans la devise de cotation, celle
    que l'utilisateur lit chez son courtier, et convertis en euros. Sans
    cette conversion, additionner une ligne saoudienne et une ligne
    parisienne dans un même total produirait un nombre qui ne veut rien
    dire — et que la page afficherait pourtant avec un symbole €.
    """
    standard_id = _standard_demande()
    evaluees, fetched_at, taux = _univers(standard_id)
    return jsonify({
        "standard": standards.get(standard_id)["label"],
        "collecte": fetched_at.isoformat() if fetched_at else None,
        "valeurs": [
            {
                "ticker": e["societe"]["ticker"],
                "nom": e["societe"]["nom"],
                "prix": e["societe"].get("prix"),
                "prix_eur": fx.en_euros(
                    e["societe"].get("prix"), e["societe"].get("currency"), taux
                ),
                "devise": e["societe"].get("currency"),
                "dividende": e["societe"].get("dividende_par_action"),
                "dividende_eur": fx.en_euros(
                    e["societe"].get("dividende_par_action"),
                    e["societe"].get("currency"), taux
                ),
                # La variation du jour permet au portefeuille d'afficher ce
                # qu'il a gagné ou perdu depuis l'ouverture, comme le fait
                # n'importe quel relevé de courtier.
                "variation": e["societe"].get("variation"),
                # Secteur et place sont traduits ici plutôt que côté client :
                # une répartition de portefeuille qui annonce « brvm » et
                # « Specialty Chemicals » sur un site français n'est pas une
                # répartition lisible.
                "secteur": vocabulaire.activite(e["societe"], _langue())
                           or vocabulaire.secteur(e["societe"].get("sector"), _langue()),
                "place": e["societe"].get("place"),
                "place_nom": (universe.PLACES.get(e["societe"].get("place") or "")
                              or {}).get("nom"),
                # Postes de bilan : ils servent à la page Zakat pour estimer
                # la part zakatable d'une société détenue à long terme.
                "cash": e["societe"].get("cash_and_investments"),
                "creances": e["societe"].get("receivables"),
                "total_assets": e["societe"].get("total_assets"),
                "verdict": e["resultat"]["verdict"],
                "raison": e["resultat"]["raison"],
            }
            for e in evaluees
        ],
    })


@app.route("/methodologie")
def methodologie():
    valeurs, _, _ = cache.index()
    collectees = {v.get("place") for v in valeurs}
    return render_template(
        "methodologie.html",
        standards=standards.STANDARDS,
        standard=standards.get(_standard_demande()),
        regions=universe.places_par_region(),
        absentes=universe.PLACES_ABSENTES,
        collectees=collectees,
        total=len(valeurs),
    )


@app.errorhandler(404)
def introuvable(_):
    return render_template("404.html"), 404


# --- Filtres de rendu ---------------------------------------------------

@app.template_filter("montant")
def f_montant(valeur):
    """Un montant à l'échelle lisible (Md / M)."""
    if valeur is None:
        return "—"
    if abs(valeur) >= 1e9:
        return f"{valeur / 1e9:,.1f} Md".replace(",", " ").replace(".", ",")
    if abs(valeur) >= 1e6:
        return f"{valeur / 1e6:,.0f} M".replace(",", " ")
    return f"{valeur:,.0f}".replace(",", " ")


@app.template_filter("euros")
def f_euros(valeur):
    """Une capitalisation convertie, avec son unité — c'est la seule
    grandeur comparable d'une place à l'autre."""
    if valeur is None:
        return "—"
    return f_montant(valeur) + " €"


@app.template_filter("devise")
def f_devise(valeur, code):
    """Un montant dans sa devise d'origine, celle que l'utilisateur
    retrouvera chez son courtier."""
    if valeur is None:
        return "—"
    if code == "GBp":
        # Yahoo cote Londres en pence : on rend des livres, plus lisibles.
        return f"{valeur / 100:,.2f} GBP".replace(",", " ").replace(".", ",")
    return f"{valeur:,.2f} {code or ''}".replace(",", " ").replace(".", ",").strip()


@app.template_filter("pourcent")
def f_pourcent(valeur):
    if valeur is None:
        return "—"
    return f"{valeur * 100:.1f} %".replace(".", ",")


@app.template_filter("nombre")
def f_nombre(valeur, decimales=2):
    if valeur is None:
        return "—"
    return f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")


@app.template_filter("signe")
def f_signe(valeur):
    """Une variation, avec son signe — pour un cours, l'absence de signe
    est une ambiguïté qu'on ne peut pas se permettre."""
    if valeur is None:
        return "—"
    return f"{'+' if valeur >= 0 else '−'}{abs(valeur) * 100:.1f} %".replace(".", ",")


@app.template_filter("date_fr")
def f_date_fr(valeur):
    if not valeur:
        return "—"
    if hasattr(valeur, "strftime"):
        return valeur.strftime("%d/%m/%Y à %Hh%M UTC")
    texte = str(valeur)
    if "T" in texte:
        texte = texte.split("T")[0]
    try:
        a, m, j = texte.split("-")
    except ValueError:
        return texte
    return f"{j}/{m}/{a}"


@app.template_filter("rendement")
def f_rendement(societe):
    """Le rendement du dividende, normalisé puis formaté (voir
    screening/analyses.py pour l'incohérence de Yahoo sur ce champ)."""
    valeur = analyses._rendement(societe)
    if not valeur:
        return "—"
    return f"{valeur * 100:.1f} %".replace(".", ",")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5001)))
