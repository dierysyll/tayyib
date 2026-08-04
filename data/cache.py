"""
Cache disque, en JSON.

Yahoo Finance limite le débit assez agressivement (HTTP 429) et une page
qui interrogerait soixante tickers à chaque visite serait à la fois lente
et vite bloquée. On rafraîchit donc l'univers hors ligne (voir refresh.py)
et l'application lit le cache.

Un effet secondaire utile : les fondamentaux d'un bilan ne changent qu'une
fois par trimestre. Les servir depuis un cache n'est pas une dégradation,
c'est le rythme naturel de la donnée. Seule la capitalisation bouge tous
les jours — d'où la date de rafraîchissement affichée dans l'interface.
"""

import json
import os
from datetime import datetime, timezone

CACHE_DIR = os.environ.get("TAYYIB_CACHE_DIR", os.path.join(os.path.dirname(__file__), "..", "cache"))
CACHE_FILE = os.path.join(CACHE_DIR, "companies.json")


def _ensure_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def save(companies):
    """Écrit l'univers dans le cache, horodaté."""
    _ensure_dir()
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "companies": companies,
    }
    # Écriture atomique : un rafraîchissement interrompu ne doit pas
    # laisser un cache tronqué que l'appli lirait au démarrage.
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CACHE_FILE)
    return CACHE_FILE


def load():
    """Renvoie (companies, fetched_at). Cache absent → ([], None), et
    c'est à l'appelant d'afficher un message utile plutôt que planter."""
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], None

    fetched_at = payload.get("fetched_at")
    if fetched_at:
        try:
            fetched_at = datetime.fromisoformat(fetched_at)
        except ValueError:
            fetched_at = None

    return payload.get("companies", []), fetched_at
