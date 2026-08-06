"""
Tayyib — le screener boursier halal, en français, pour le monde entier.

Le nom vient de « halalan tayyiban » : licite, et pur.

L'application est volontairement mince. Toute la matière est dans
screening/ (les règles et les analyses), data/ (la collecte) et charts.py
(la projection SVG) ; ici on ne fait que router, filtrer, trier et rendre.
"""

import os

from flask import Flask, abort, jsonify, render_template, request

import charts
from data import cache, fx, universe
from screening import analyses, engine, standards

app = Flask(__name__)

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
    evaluees = [
        {"societe": s, "resultat": engine.evaluate(s, standard_id)}
        for s in valeurs
    ]
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

    secteurs = sorted({
        e["societe"]["sector"] for e in portee if e["societe"].get("sector")
    })

    return render_template(
        "index.html",
        evaluees=evaluees,
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

    return render_template(
        "valeur.html",
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

    return render_template(
        "analyses.html",
        entrees=entrees[:12],
        sorties=sorties[:12],
        nb_entrees=len(entrees),
        nb_sorties=len(sorties),
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


@app.route("/actualites")
def actualites():
    standard_id = _standard_demande()
    articles, collecte = cache.actus()
    valeurs, _, _ = cache.index()

    # On rattache à chaque article le verdict de la valeur concernée : lire
    # une actualité sur une société non conforme sans le savoir n'aurait
    # aucun intérêt ici.
    index_valeurs = {v["ticker"]: v for v in valeurs}
    enrichis = []
    for article in articles:
        societe = index_valeurs.get(article.get("ticker"))
        enrichis.append({
            **article,
            "societe": societe,
            "verdict": engine.evaluate(societe, standard_id)["verdict"] if societe else None,
            "place": universe.PLACES.get(societe.get("place")) if societe else None,
        })

    filtre = request.args.get("verdict")
    if filtre in ORDRE_VERDICT:
        enrichis = [a for a in enrichis if a["verdict"] == filtre]

    return render_template(
        "actualites.html",
        articles=enrichis[:60],
        total=len(articles),
        filtre=filtre,
        collecte=collecte,
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
        engine=engine,
    )


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
    """La zakat sur un portefeuille d'actions."""
    _, _, _ = cache.index()
    metaux = cache.metaux()
    return render_template(
        "zakat.html",
        metaux=metaux,
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
                "secteur": e["societe"].get("industry") or e["societe"].get("sector"),
                "place": e["societe"].get("place"),
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
