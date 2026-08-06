"""
Cache disque, en JSON, scindé en deux étages.

Yahoo Finance limite le débit assez agressivement (HTTP 429) et une page
qui interrogerait mille tickers à chaque visite serait à la fois lente et
vite bloquée. On rafraîchit donc l'univers hors ligne (voir refresh.py) et
l'application lit le cache.

Un effet secondaire utile : les fondamentaux d'un bilan ne changent qu'une
fois par trimestre. Les servir depuis un cache n'est pas une dégradation,
c'est le rythme naturel de la donnée. Seules la capitalisation et le cours
bougent tous les jours — d'où la date de collecte affichée dans l'interface.


Pourquoi deux étages
--------------------
Tant que l'univers tenait à la place de Paris, un fichier unique suffisait.
À plus de mille valeurs, il pèserait une vingtaine de mégaoctets, dont
l'écrasante majorité en historiques de cours — six ans de points
hebdomadaires par société. Or l'écran principal, le screener, n'a besoin
d'aucun de ces points : il lui faut un nom, un secteur, trois montants de
bilan et une capitalisation.

On sépare donc :

  cache/index.json          l'essentiel de chaque valeur, plus les taux de
                            change du jour. Quelques mégaoctets, chargés
                            une fois en mémoire et servis à toutes les
                            pages de liste ;
  cache/valeurs/<sym>.json  le détail d'une société — historique de cours,
                            comptes annuels, dividendes, description. Lu à
                            la demande, uniquement quand on ouvre sa fiche.

Le gain n'est pas qu'une affaire de mémoire : c'est ce qui garde le
screener instantané quand l'univers grandit.
"""

import json
import os
import time
from datetime import datetime, timezone

CACHE_DIR = os.environ.get(
    "TAYYIB_CACHE_DIR", os.path.join(os.path.dirname(__file__), "..", "cache")
)
INDEX_FILE = os.path.join(CACHE_DIR, "index.json")
DETAILS_DIR = os.path.join(CACHE_DIR, "valeurs")

# L'ancien cache monolithique. On sait encore le lire : pendant une
# collecte longue, il permet au site de continuer à servir la version
# précédente au lieu d'afficher un univers vide.
LEGACY_FILE = os.path.join(CACHE_DIR, "companies.json")

# Les champs que le screener, les classements et les analyses utilisent.
# Tout le reste part dans le fichier de détail.
CHAMPS_INDEX = (
    "ticker", "nom", "place", "sector", "industry", "currency", "pays",
    "market_cap", "market_cap_eur", "prix", "rendement",
    "dividende_par_action", "total_debt", "cash_and_investments",
    "receivables", "total_assets", "bilan_date", "historique",
)


def _ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(DETAILS_DIR, exist_ok=True)


def _ecrire(chemin, payload):
    """Écriture atomique : un rafraîchissement interrompu ne doit pas
    laisser un fichier tronqué que l'appli lirait au démarrage."""
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, chemin)


def _nom_fichier(ticker):
    """Un symbole peut contenir des caractères qui ne font pas un bon nom de
    fichier (`BRK-B`, `M&M.NS`, `HM-B.ST`). On les neutralise."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in ticker) + ".json"


def resume_index(societe):
    """La version allégée d'une société, telle qu'elle entre dans l'index."""
    return {cle: societe.get(cle) for cle in CHAMPS_INDEX}


def save_detail(societe):
    """Écrit le détail complet d'une société."""
    _ensure_dirs()
    chemin = os.path.join(DETAILS_DIR, _nom_fichier(societe["ticker"]))
    _ecrire(chemin, societe)
    return chemin


def save_index(societes, taux=None, metaux_=None):
    """Écrit l'index, horodaté, avec les taux de change de la collecte et
    le cours des métaux (pour le nissab de la zakat)."""
    _ensure_dirs()
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "taux": taux or {},
        "valeurs": [resume_index(s) for s in societes],
    }
    # Une collecte qui n'a pas pu lire l'or ne doit pas effacer le dernier
    # cours connu : mieux vaut un nissab d'hier qu'aucun nissab.
    payload["metaux"] = metaux_ or _metaux_precedents()
    _ecrire(INDEX_FILE, payload)
    return INDEX_FILE


def _metaux_precedents():
    try:
        with open(INDEX_FILE, encoding="utf-8") as f:
            return json.load(f).get("metaux") or {}
    except (OSError, json.JSONDecodeError):
        return {}


_MEMO_METAUX = {"mtime": None, "valeur": {}}


def metaux():
    """Cours de l'or et de l'argent, et nissab correspondant. {} si absent."""
    try:
        mtime = os.path.getmtime(INDEX_FILE)
    except OSError:
        return {}

    if _MEMO_METAUX["mtime"] == mtime:
        return _MEMO_METAUX["valeur"]

    try:
        with open(INDEX_FILE, encoding="utf-8") as f:
            valeur = json.load(f).get("metaux") or {}
    except (OSError, json.JSONDecodeError):
        return {}

    _MEMO_METAUX["mtime"], _MEMO_METAUX["valeur"] = mtime, valeur
    return valeur


# L'index fait quelques mégaoctets : le reparser à chaque requête coûterait
# plus cher que tout le screening réuni. On le garde en mémoire, avec la
# date de modification du fichier comme clé — un `refresh.py` qui passe est
# ainsi pris en compte sans redémarrage.
_MEMO = {"mtime": None, "valeur": None}


def _lire_legacy():
    """Repli sur l'ancien cache monolithique, le temps d'une migration."""
    try:
        with open(LEGACY_FILE, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], None, {}

    fetched_at = _date(payload.get("fetched_at"))
    valeurs = [resume_index(s) for s in payload.get("companies", [])]
    return valeurs, fetched_at, {}


def _date(brut):
    if not brut:
        return None
    try:
        return datetime.fromisoformat(brut)
    except (ValueError, TypeError):
        return None


def index():
    """Renvoie (valeurs, fetched_at, taux).

    Index absent → on tente l'ancien cache, puis on renvoie un univers vide.
    C'est à l'appelant d'afficher un message utile plutôt que de planter.
    """
    try:
        mtime = os.path.getmtime(INDEX_FILE)
    except OSError:
        return _lire_legacy()

    if _MEMO["mtime"] == mtime:
        return _MEMO["valeur"]

    try:
        with open(INDEX_FILE, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return _lire_legacy()

    resultat = (
        payload.get("valeurs", []),
        _date(payload.get("fetched_at")),
        payload.get("taux", {}),
    )
    _MEMO["mtime"], _MEMO["valeur"] = mtime, resultat
    return resultat


# Les fiches valeur sont consultées en rafale sur les mêmes titres (on
# revient au screener, on rouvre une voisine). Un petit cache borné évite
# de relire le disque à chaque fois sans risquer de garder mille détails
# en mémoire.
_DETAILS = {}
_DETAILS_MAX = 64


def detail(ticker):
    """Le détail complet d'une société, ou None s'il n'a pas été collecté."""
    if ticker in _DETAILS:
        return _DETAILS[ticker]

    chemin = os.path.join(DETAILS_DIR, _nom_fichier(ticker))
    try:
        with open(chemin, encoding="utf-8") as f:
            societe = json.load(f)
    except (OSError, json.JSONDecodeError):
        return _detail_legacy(ticker)

    if len(_DETAILS) >= _DETAILS_MAX:
        _DETAILS.clear()
    _DETAILS[ticker] = societe
    return societe


def _detail_legacy(ticker):
    """Le détail d'une valeur encore servie par l'ancien cache."""
    try:
        with open(LEGACY_FILE, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    for societe in payload.get("companies", []):
        if societe.get("ticker") == ticker:
            return societe
    return None


# --- Fil d'actualité ----------------------------------------------------

ACTUS_FILE = os.path.join(CACHE_DIR, "actus.json")


def save_actus(articles):
    _ensure_dirs()
    _ecrire(ACTUS_FILE, {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
    })
    return ACTUS_FILE


def actus():
    """Renvoie (articles, fetched_at). Fichier absent → ([], None)."""
    try:
        with open(ACTUS_FILE, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], None
    return payload.get("articles", []), _date(payload.get("fetched_at"))


# Le fil de presse francophone est stocké à part des dépêches Yahoo : les
# deux n'ont ni la même source, ni la même fraîcheur, ni le même usage.
PRESSE_FILE = os.path.join(CACHE_DIR, "presse.json")


def save_presse(articles):
    _ensure_dirs()
    _ecrire(PRESSE_FILE, {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
    })
    return PRESSE_FILE


def presse():
    """Renvoie (articles, fetched_at). Fichier absent → ([], None)."""
    try:
        with open(PRESSE_FILE, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], None
    return payload.get("articles", []), _date(payload.get("fetched_at"))


# --- Cours journaliers ---------------------------------------------------
#
# Récupérés à la demande, une valeur à la fois (voir la route /api/cours).
# Ils vivent dans leur propre dossier plutôt que dans le fichier de détail :
# on veut pouvoir les périmer — un cours du jour vieillit en un jour — sans
# toucher aux comptes annuels, qui ne bougent qu'une fois par exercice.

COURS_DIR = os.path.join(CACHE_DIR, "cours")

# Au-delà, on redemande : le dernier point serait d'hier.
COURS_FRAICHEUR = 12 * 3600


def save_cours_journalier(ticker, points):
    os.makedirs(COURS_DIR, exist_ok=True)
    chemin = os.path.join(COURS_DIR, _nom_fichier(ticker))
    _ecrire(chemin, {"ticker": ticker, "points": points})
    return chemin


def cours_journalier(ticker):
    """Les points journaliers en cache, ou None s'ils manquent ou ont vieilli."""
    chemin = os.path.join(COURS_DIR, _nom_fichier(ticker))
    try:
        if time.time() - os.path.getmtime(chemin) > COURS_FRAICHEUR:
            return None
        with open(chemin, encoding="utf-8") as f:
            return json.load(f).get("points")
    except (OSError, json.JSONDecodeError):
        return None


def deja_collectes():
    """Les symboles dont le détail est déjà sur disque, avec leur date de
    collecte. C'est ce qui permet à refresh.py de reprendre une collecte
    interrompue sans tout redemander à Yahoo."""
    try:
        fichiers = os.listdir(DETAILS_DIR)
    except OSError:
        return {}

    dates = {}
    for nom in fichiers:
        if not nom.endswith(".json"):
            continue
        chemin = os.path.join(DETAILS_DIR, nom)
        try:
            with open(chemin, encoding="utf-8") as f:
                societe = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if societe.get("ticker"):
            dates[societe["ticker"]] = os.path.getmtime(chemin)
    return dates


def charger_details(tickers):
    """Recharge les détails déjà sur disque, pour réécrire un index complet
    après une collecte partielle."""
    societes = []
    for ticker in tickers:
        societe = detail(ticker)
        if societe:
            societes.append(societe)
    return societes


# --- Compatibilité ------------------------------------------------------

def load():
    """Ancienne signature (valeurs, fetched_at), conservée le temps que tous
    les appelants passent à `index()`."""
    valeurs, fetched_at, _ = index()
    return valeurs, fetched_at
