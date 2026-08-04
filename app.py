"""
Tayyib — screener boursier halal pour la place de Paris.

Le nom vient de « halalan tayyiban » : licite, et pur.

L'application est volontairement mince. Toute la matière est dans
screening/ (les règles) et data/ (la collecte) ; ici on ne fait que router,
trier et rendre.
"""

import os

from flask import Flask, abort, render_template, request

from data import cache
from screening import engine, standards

app = Flask(__name__)

# Ordre d'affichage : ce qu'on peut acheter d'abord, ce qui est exclu en
# dernier. Un screener sert à trouver, pas à parcourir des rejets.
ORDRE_VERDICT = {
    engine.CONFORME: 0,
    engine.A_VERIFIER: 1,
    engine.NON_CONFORME: 2,
}


def _univers(standard_id):
    """L'univers évalué selon un standard, trié, avec la date de collecte."""
    societes, fetched_at = cache.load()

    evaluees = []
    for societe in societes:
        resultat = engine.evaluate(societe, standard_id)
        evaluees.append({"societe": societe, "resultat": resultat})

    evaluees.sort(key=lambda e: (
        ORDRE_VERDICT[e["resultat"]["verdict"]],
        -(e["societe"].get("market_cap") or 0),
    ))
    return evaluees, fetched_at


def _standard_demande():
    return request.args.get("standard", standards.DEFAULT_STANDARD)


@app.route("/")
def accueil():
    standard_id = _standard_demande()
    evaluees, fetched_at = _univers(standard_id)

    q = (request.args.get("q") or "").strip()
    if q:
        terme = q.lower()
        evaluees = [
            e for e in evaluees
            if terme in e["societe"]["nom"].lower()
            or terme in e["societe"]["ticker"].lower()
        ]

    filtre = request.args.get("verdict")
    if filtre in ORDRE_VERDICT:
        evaluees = [e for e in evaluees if e["resultat"]["verdict"] == filtre]

    # Les compteurs portent sur l'univers entier, pas sur la vue filtrée :
    # ils servent de repère, pas de description du tableau affiché.
    tous, _ = _univers(standard_id)
    compteurs = {
        v: sum(1 for e in tous if e["resultat"]["verdict"] == v)
        for v in ORDRE_VERDICT
    }

    return render_template(
        "index.html",
        evaluees=evaluees,
        compteurs=compteurs,
        total=len(tous),
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
        fetched_at=fetched_at,
        q=q,
        filtre=filtre,
        engine=engine,
    )


@app.route("/valeur/<ticker>")
def valeur(ticker):
    standard_id = _standard_demande()
    societes, fetched_at = cache.load()

    societe = next((s for s in societes if s["ticker"].lower() == ticker.lower()), None)
    if societe is None:
        abort(404)

    # Le même titre selon les trois standards : c'est souvent là que le
    # lecteur comprend que « halal » n'est pas une propriété binaire de
    # l'entreprise, mais le résultat d'une convention de calcul.
    comparaison = [
        {"standard": std, "resultat": engine.evaluate(societe, sid)}
        for sid, std in standards.STANDARDS.items()
    ]

    return render_template(
        "valeur.html",
        societe=societe,
        resultat=engine.evaluate(societe, standard_id),
        comparaison=comparaison,
        standard=standards.get(standard_id),
        standards=standards.STANDARDS,
        fetched_at=fetched_at,
        engine=engine,
    )


@app.route("/methodologie")
def methodologie():
    return render_template(
        "methodologie.html",
        standards=standards.STANDARDS,
        standard=standards.get(_standard_demande()),
    )


@app.errorhandler(404)
def introuvable(_):
    return render_template("404.html"), 404


# --- Filtres de rendu ---------------------------------------------------

@app.template_filter("montant")
def f_montant(valeur):
    """Un montant en euros, à l'échelle lisible (Md / M)."""
    if valeur is None:
        return "—"
    if abs(valeur) >= 1e9:
        return f"{valeur / 1e9:,.1f} Md".replace(",", " ").replace(".", ",")
    if abs(valeur) >= 1e6:
        return f"{valeur / 1e6:,.0f} M".replace(",", " ")
    return f"{valeur:,.0f}".replace(",", " ")


@app.template_filter("pourcent")
def f_pourcent(valeur):
    if valeur is None:
        return "—"
    return f"{valeur * 100:.1f} %".replace(".", ",")


@app.template_filter("date_fr")
def f_date_fr(valeur):
    if not valeur:
        return "—"
    if hasattr(valeur, "strftime"):
        return valeur.strftime("%d/%m/%Y à %Hh%M UTC")
    a, m, j = str(valeur).split("-")
    return f"{j}/{m}/{a}"


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5001)))
