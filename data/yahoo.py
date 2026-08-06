"""
Source de données : Yahoo Finance, via yfinance.

Un choix important est fait ici. Yahoo expose deux gisements pour les
mêmes grandeurs :

  - `ticker.info`, un dictionnaire de synthèse (`totalDebt`, `totalCash`…) ;
  - `ticker.balance_sheet`, le bilan publié, daté.

Ils ne concordent pas. Sur L'Oréal, `info["totalCash"]` annonce 4,05 Md€
quand le bilan au 31/12/2025 porte 9,90 Md€ de trésorerie et placements
court terme. `info` agrège des périodes hétérogènes et ne dit pas
lesquelles.

On lit donc le bilan, et uniquement lui, pour tout ce qui entre dans les
ratios : les trois montants proviennent du même arrêté comptable, et cet
arrêté est affiché à l'utilisateur. Un ratio dont on ne peut pas nommer la
date n'est pas vérifiable, et un screening invérifiable ne vaut rien.


Reconstituer la capitalisation passée
-------------------------------------
Le bilan porte, pour chaque exercice, le **nombre d'actions en
circulation** à cette date. Croisé avec le cours de clôture de la même
semaine, il donne la capitalisation boursière de l'époque — et donc des
ratios AAOIFI historiques réels, non approchés.

Deux précautions rendent ce calcul juste :

  - l'historique est demandé en `auto_adjust=False`. Les cours ajustés
    rétropropagent les dividendes et minorent le passé ; ils donneraient
    une capitalisation trop faible, donc des ratios trop élevés, donc des
    « non conforme » à tort ;
  - le nombre d'actions vient du même arrêté que la dette. Cours réel ×
    actions réelles à la même date : les éventuelles divisions d'action
    se neutralisent d'elles-mêmes.
"""

import yfinance as yf

from data.presse import sans_emoji


class SourceIndisponible(Exception):
    """Yahoo nous a bloqués — la donnée existe, on n'y a pas accès.

    C'est une distinction qui a l'air technique et qui ne l'est pas. Un
    symbole absent du catalogue et un symbole qu'on n'a pas pu lire
    produisent le même silence, mais appellent des réponses opposées :
    le premier doit être retiré de l'univers, le second redemandé plus
    tard. Les confondre revient à supprimer une place entière du produit
    parce qu'on a interrogé Yahoo trop vite — ce qui est exactement ce qui
    s'est produit tant que cette exception n'existait pas.
    """


def _est_blocage(exc):
    nom = type(exc).__name__.lower()
    texte = str(exc).lower()
    return (
        "ratelimit" in nom
        or "429" in texte
        or "too many requests" in texte
        or "unauthorized" in texte
        or "401" in texte
    )


def _appel(fonction, *args, **kwargs):
    """Un appel à Yahoo. Renvoie None sur erreur ordinaire, mais laisse
    remonter un blocage pour que l'appelant puisse réessayer plus tard."""
    try:
        return fonction(*args, **kwargs)
    except Exception as exc:
        if _est_blocage(exc):
            raise SourceIndisponible(str(exc)[:120]) from exc
        return None

# Pour chaque grandeur, les lignes de bilan acceptées, par ordre de
# préférence. Yahoo ne publie pas exactement le même plan comptable selon
# les sociétés, d'où les replis.
BILAN_ROWS = {
    "total_debt": [
        "Total Debt",
        "Long Term Debt And Capital Lease Obligation",
    ],
    "cash_and_investments": [
        "Cash Cash Equivalents And Short Term Investments",
        "Cash And Cash Equivalents",
    ],
    "receivables": [
        "Accounts Receivable",
        "Receivables",
        "Gross Accounts Receivable",
    ],
    "total_assets": [
        "Total Assets",
    ],
    "actions": [
        "Ordinary Shares Number",
        "Share Issued",
    ],
}

COMPTE_RESULTAT_ROWS = {
    "revenu": ["Total Revenue"],
    "resultat_net": ["Net Income Common Stockholders", "Net Income"],
    "resultat_exploitation": ["Operating Income", "Total Operating Income As Reported"],
    "marge_brute": ["Gross Profit"],
}

# Cinq ans d'historique hebdomadaire : assez pour couvrir les quatre
# exercices que Yahoo publie, sans alourdir le cache inutilement.
HISTORIQUE_PERIODE = "6y"


def _pick(tableau, colonne, noms):
    """Première ligne présente et renseignée parmi `noms`."""
    for nom in noms:
        if nom in tableau.index:
            valeur = tableau.loc[nom, colonne]
            if valeur is not None and valeur == valeur:  # NaN != NaN
                return float(valeur)
    return None


def _cours_a_la_date(historique, date_arrete):
    """Dernier cours de clôture connu à la date d'arrêté du bilan.

    On prend le point le plus récent *antérieur ou égal* à l'arrêté :
    l'exercice se clôt souvent un jour férié ou un week-end.
    """
    if historique is None or historique.empty:
        return None
    cible = date_arrete
    if historique.index.tz is not None and cible.tzinfo is None:
        cible = cible.tz_localize(historique.index.tz)
    anterieurs = historique.index[historique.index <= cible]
    if len(anterieurs) == 0:
        return None
    return float(historique.loc[anterieurs[-1], "Close"])


def fetch(ticker):
    """Récupère une société.

    Renvoie un dictionnaire, ou None si Yahoo ne connaît pas le symbole.
    Lève `SourceIndisponible` si nous sommes bloqués : l'appelant doit
    alors réessayer, surtout pas conclure que le symbole n'existe pas.
    """
    t = yf.Ticker(ticker)

    info = _appel(lambda: t.info) or {}

    if not info.get("shortName") and not info.get("longName"):
        return None

    societe = {
        "ticker": ticker,
        "nom": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency"),
        "pays": info.get("country"),
        "market_cap": info.get("marketCap"),
        "prix": info.get("currentPrice") or info.get("regularMarketPrice"),
        "dividende_par_action": info.get("dividendRate"),
        "rendement": info.get("dividendYield"),
        "site": info.get("website"),
        "resume": info.get("longBusinessSummary"),
        "salaries": info.get("fullTimeEmployees"),
        # Multiples de valorisation : ils ne servent pas au screening, mais
        # c'est ce qu'on vient chercher sur une fiche valeur.
        "valorisation": {
            "per": info.get("trailingPE"),
            "per_estime": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "valeur_entreprise": info.get("enterpriseValue"),
            "beta": info.get("beta"),
            "plus_haut_52s": info.get("fiftyTwoWeekHigh"),
            "plus_bas_52s": info.get("fiftyTwoWeekLow"),
            "actions": info.get("sharesOutstanding"),
            "marge_nette": info.get("profitMargins"),
            "roe": info.get("returnOnEquity"),
        },
        # Renseignés depuis les états financiers ci-dessous.
        "total_debt": None,
        "cash_and_investments": None,
        "receivables": None,
        "total_assets": None,
        "bilan_date": None,
        "historique": [],
        "cours": [],
        "dividendes": [],
    }

    # --- Historique de cours (non ajusté : voir l'en-tête du module) ----
    historique_cours = _appel(
        t.history, period=HISTORIQUE_PERIODE, interval="1wk", auto_adjust=False
    )

    if historique_cours is not None and not historique_cours.empty:
        societe["cours"] = [
            [d.date().isoformat(), round(float(c), 2)]
            for d, c in historique_cours["Close"].items()
            if c == c
        ]

    # --- Bilan et compte de résultat, exercice par exercice -------------
    # Le bilan est la pièce maîtresse : sans lui, aucun ratio n'est
    # calculable et la valeur tomberait à tort en « à vérifier ». Un
    # blocage sur cet appel doit donc interrompre la collecte du titre
    # plutôt que produire une fiche amputée.
    bilan = _appel(lambda: t.balance_sheet)
    compte = _appel(lambda: t.income_stmt)

    if bilan is not None and not bilan.empty:
        for colonne in bilan.columns:
            periode = {"date": colonne.date().isoformat()}
            for cle, noms in BILAN_ROWS.items():
                periode[cle] = _pick(bilan, colonne, noms)

            # Un exercice sans dette ni total de bilan n'est pas exploitable
            # (Yahoo publie parfois une colonne vide en fin de série).
            if periode["total_debt"] is None and periode["total_assets"] is None:
                continue

            if compte is not None and not compte.empty and colonne in compte.columns:
                for cle, noms in COMPTE_RESULTAT_ROWS.items():
                    periode[cle] = _pick(compte, colonne, noms)

            cours = _cours_a_la_date(historique_cours, colonne)
            periode["cours"] = cours
            periode["market_cap"] = (
                cours * periode["actions"]
                if cours and periode.get("actions")
                else None
            )
            societe["historique"].append(periode)

            # Le premier exercice *retenu* alimente les champs « courants »,
            # ceux qui servent au verdict affiché par défaut.
            #
            # « Retenu », et non « premier de la liste » : Yahoo publie
            # parfois une colonne de tête vide, qu'on écarte plus haut. La
            # version précédente testait l'indice d'énumération, si bien que
            # la fiche restait sans bilan — donc « à vérifier » — alors que
            # l'historique en portait un et concluait « conforme ». Les deux
            # écrans se contredisaient sur la même société.
            if len(societe["historique"]) == 1:
                societe["bilan_date"] = periode["date"]
                for cle in BILAN_ROWS:
                    societe[cle] = periode[cle]

    # --- Dividendes -----------------------------------------------------
    dividendes = _appel(lambda: t.dividends)

    if dividendes is not None and len(dividendes):
        societe["dividendes"] = [
            [d.date().isoformat(), round(float(m), 4)]
            for d, m in dividendes.items()
        ][-20:]

    return societe


def fetch_cours_journalier(ticker, periode="2y"):
    """L'historique de cours en pas journalier, pour une seule valeur.

    La collecte de masse se contente d'un point par semaine sur six ans :
    c'est ce qu'il faut pour situer des arrêtés comptables, et ce serait
    plus de vingt mégaoctets de cache si on descendait au jour pour mille
    valeurs. Le pas journalier est donc demandé à la demande, valeur par
    valeur, quand quelqu'un ouvre une fiche et veut lire un mois.

    Comme pour l'hebdomadaire, `auto_adjust=False` : les cours ajustés
    rétropropagent les dividendes et déforment le passé.
    """
    historique = _appel(
        yf.Ticker(ticker).history,
        period=periode, interval="1d", auto_adjust=False,
    )
    if historique is None or historique.empty:
        return []
    return [
        [d.date().isoformat(), round(float(c), 4)]
        for d, c in historique["Close"].items()
        if c == c
    ]


# --- Actualités -----------------------------------------------------------
#
# yfinance a changé la forme de `Ticker.news` en cours de route : l'ancienne
# version renvoyait un dictionnaire plat (`title`, `link`,
# `providerPublishTime`), la nouvelle emboîte tout sous `content`. On lit
# les deux plutôt que d'épingler une version, parce qu'une mise à jour de
# dépendance ne doit pas vider silencieusement une rubrique du site.

def _texte(*candidats):
    for valeur in candidats:
        if isinstance(valeur, str) and valeur.strip():
            return valeur.strip()
    return None


def _article(brut, ticker):
    contenu = brut.get("content") if isinstance(brut.get("content"), dict) else {}

    titre = _texte(contenu.get("title"), brut.get("title"))
    if not titre:
        return None

    lien = _texte(
        (contenu.get("canonicalUrl") or {}).get("url") if isinstance(contenu.get("canonicalUrl"), dict) else None,
        (contenu.get("clickThroughUrl") or {}).get("url") if isinstance(contenu.get("clickThroughUrl"), dict) else None,
        brut.get("link"),
    )
    if not lien:
        return None

    source = _texte(
        (contenu.get("provider") or {}).get("displayName") if isinstance(contenu.get("provider"), dict) else None,
        brut.get("publisher"),
    )

    # Deux formats de date : ISO 8601 côté nouveau, horodatage Unix côté
    # ancien. On normalise en ISO, la seule forme que le gabarit sait lire.
    publie = _texte(contenu.get("pubDate"), contenu.get("displayTime"))
    if not publie and brut.get("providerPublishTime"):
        from datetime import datetime, timezone
        try:
            publie = datetime.fromtimestamp(
                int(brut["providerPublishTime"]), tz=timezone.utc
            ).isoformat()
        except (ValueError, OSError, OverflowError):
            publie = None

    # Même nettoyage que pour la presse : l'interface n'emploie aucun emoji,
    # les titres agrégés ne doivent pas en réintroduire.
    return {
        "ticker": ticker,
        "titre": sans_emoji(titre),
        "lien": lien,
        "source": source,
        "publie": publie,
        "resume": sans_emoji(_texte(contenu.get("summary"), contenu.get("description"))),
    }


def fetch_news(ticker, limite=6):
    """Les derniers articles Yahoo attachés à une valeur.

    Renvoie une liste, éventuellement vide : l'absence d'actualité sur un
    titre est banale et ne doit pas être traitée comme une erreur.
    """
    # Une rubrique d'actualité vide est bénigne : ici on avale tout, y
    # compris un blocage, plutôt que d'interrompre la collecte.
    try:
        brut = yf.Ticker(ticker).news or []
    except Exception:
        return []

    articles = []
    for item in brut:
        if not isinstance(item, dict):
            continue
        article = _article(item, ticker)
        if article:
            articles.append(article)
        if len(articles) >= limite:
            break
    return articles
