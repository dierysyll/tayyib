"""
Rafraîchit le cache de l'univers.

    python refresh.py

À lancer à la main, ou par une tâche planifiée quotidienne. Yahoo limite
le débit : on espace les appels et on garde la valeur déjà en cache quand
un ticker échoue, plutôt que de perdre une société sur un 429 passager.
"""

import sys
import time

from data import cache, universe, yahoo

PAUSE = 0.4  # secondes entre deux tickers, pour rester sous le radar de Yahoo


def main():
    anciennes = {c["ticker"]: c for c in cache.load()[0]}
    societes, echecs = [], []

    for i, ticker in enumerate(universe.UNIVERSE, 1):
        try:
            societe = yahoo.fetch(ticker)
        except Exception as e:
            societe, erreur = None, str(e)[:60]
        else:
            erreur = "inconnu de Yahoo"

        if societe:
            societes.append(societe)
            etat = f"{societe['nom'][:34]:36} {societe.get('sector') or '—'}"
        elif ticker in anciennes:
            societes.append(anciennes[ticker])
            echecs.append(ticker)
            etat = f"échec ({erreur}) — on garde la version en cache"
        else:
            echecs.append(ticker)
            etat = f"échec ({erreur}) — aucune version en cache"

        print(f"[{i:2}/{len(universe.UNIVERSE)}] {ticker:10} {etat}")
        time.sleep(PAUSE)

    chemin = cache.save(societes)
    print(f"\n{len(societes)} sociétés écrites dans {chemin}")
    if echecs:
        print(f"{len(echecs)} en échec : {', '.join(echecs)}")
    return 0 if societes else 1


if __name__ == "__main__":
    sys.exit(main())
