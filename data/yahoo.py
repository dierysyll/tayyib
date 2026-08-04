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

Seule la capitalisation boursière vient de `info` — par nature, elle est
au cours du jour.
"""

import yfinance as yf

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
}


def _pick(bilan, colonne, noms):
    """Première ligne présente et renseignée parmi `noms`."""
    for nom in noms:
        if nom in bilan.index:
            valeur = bilan.loc[nom, colonne]
            if valeur is not None and valeur == valeur:  # NaN != NaN
                return float(valeur)
    return None


def fetch(ticker):
    """Récupère une société. Renvoie un dictionnaire, ou None si Yahoo ne
    connaît pas le ticker (l'appelant décide quoi en faire)."""
    t = yf.Ticker(ticker)

    try:
        info = t.info or {}
    except Exception:
        return None

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
        # Renseignés depuis le bilan ci-dessous.
        "total_debt": None,
        "cash_and_investments": None,
        "receivables": None,
        "total_assets": None,
        "bilan_date": None,
    }

    try:
        bilan = t.balance_sheet
    except Exception:
        bilan = None

    if bilan is not None and not bilan.empty:
        colonne = bilan.columns[0]  # l'arrêté le plus récent
        societe["bilan_date"] = colonne.date().isoformat()
        for cle, noms in BILAN_ROWS.items():
            societe[cle] = _pick(bilan, colonne, noms)

    return societe
