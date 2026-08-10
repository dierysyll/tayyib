"""
Rafraîchit le cache de l'univers.

    python refresh.py                  collecte complète (taux, valeurs, actus)
    python refresh.py --force          ignore la reprise, tout redemander
    python refresh.py --places paris,riyad    seulement ces places
    python refresh.py --actus          seulement le fil d'actualité
    python refresh.py --index          réécrit l'index depuis le disque

À lancer à la main, ou par une tâche planifiée quotidienne.

Trois précautions, toutes dictées par la même contrainte : Yahoo limite le
débit, et une collecte de plus de mille valeurs le déclenche à coup sûr si
on s'y prend mal.

  1. **Parallélisme mesuré.** Quatre requêtes simultanées passent ;
     au-delà, on récolte des HTTP 429 en rafale. Ce n'est pas la peine
     d'aller plus vite pour se faire bloquer à mi-parcours.

  2. **Reprise.** Un symbole dont le détail est déjà sur disque et daté de
     moins de `FRAICHEUR` heures n'est pas redemandé. Une collecte
     interrompue se relance sans repartir de zéro — et sans repasser une
     heure sur des données qu'on a déjà.

  3. **Index écrit en cours de route.** Toutes les `PALIER` valeurs, l'index
     est réécrit. Le site sert donc un univers qui grandit pendant la
     collecte, au lieu d'attendre la fin pour tout basculer d'un coup.

Une valeur qui échoue conserve sa version en cache : on ne perd pas une
société sur un 429 passager.
"""

import argparse
import concurrent.futures as cf
import random
import sys
import threading
import time

from data import brvm, cache, fx, presse, universe, yahoo

TRAVAILLEURS = 3      # requêtes simultanées vers Yahoo
PAUSE = 0.35          # secondes entre deux départs, par travailleur
FRAICHEUR = 20 * 3600  # au-delà, une valeur en cache est considérée périmée
PALIER = 40           # écriture de l'index toutes les N valeurs
RETENTES = 4          # tentatives en cas de blocage

# Attente après un blocage, en secondes. Yahoo ne débloque pas en trois
# secondes : la première version de ce fichier réessayait beaucoup trop
# vite, épuisait ses tentatives et concluait à tort que le symbole
# n'existait pas. Comme tous les travailleurs se font bloquer ensemble,
# ces pauses jouent de fait le rôle d'un refroidissement global.
ATTENTES = [45, 120, 300]

# Les actualités sont collectées sur les plus grosses valeurs seulement :
# un fil de mille titres n'est pas un fil, et chaque appel est une requête
# de plus vers une source qui nous limite déjà.
ACTUS_VALEURS = 60

_verrou = threading.Lock()


def _devises():
    """Les devises à collecter.

    Celles des places screenées, plus celles dans lesquelles un utilisateur
    peut détenir des avoirs : la zakat porte sur un patrimoine, pas sur un
    portefeuille d'actions, et le convertisseur doit connaître le franc CFA
    même si aucune place n'y cote.
    """
    return universe.devises() + [d["code"] for d in fx.DEVISES_USUELLES]


def _collecte_une(ticker):
    """Une société, avec longues retentes en cas de blocage.

    Renvoie (societe, erreur). `societe` à None avec `erreur` à None
    signifie que Yahoo ne connaît pas le symbole — c'est le seul cas où
    l'on peut conclure à une absence réelle.
    """
    for tentative in range(RETENTES):
        try:
            return yahoo.fetch(ticker), None
        except yahoo.SourceIndisponible:
            if tentative == RETENTES - 1:
                return None, "bloqué par Yahoo (à relancer)"
            # Attente longue et bruitée : si tous les travailleurs
            # repartent en même temps, on se refait bloquer aussitôt.
            time.sleep(ATTENTES[tentative] + random.uniform(0, 8))
        except Exception as exc:
            return None, str(exc)[:60]
    return None, "bloqué par Yahoo (à relancer)"


def _places_demandees(arg):
    if not arg:
        return list(universe.PLACES)
    demandees = [p.strip() for p in arg.split(",") if p.strip()]
    inconnues = [p for p in demandees if p not in universe.PLACES]
    if inconnues:
        print(f"Places inconnues : {', '.join(inconnues)}")
        print(f"Places disponibles : {', '.join(universe.PLACES)}")
        sys.exit(2)
    return demandees


def collecte_valeurs(places, force=False):
    """Collecte les sociétés des places demandées. Renvoie (collectées, échecs)."""
    index_place = universe.place_par_ticker()

    # Les places que nous collectons nous-mêmes sortent de la boucle Yahoo :
    # interroger la BRVM valeur par valeur serait absurde, sa cote entière
    # tient dans une seule page.
    for place_id in places:
        if universe.PLACES[place_id].get("source") == "brvm":
            collecte_brvm()

    a_faire = []
    vus = set()
    for place_id in places:
        if universe.PLACES[place_id].get("source"):
            continue
        for ticker in universe.PLACES[place_id]["valeurs"]:
            if ticker not in vus:
                vus.add(ticker)
                a_faire.append(ticker)

    connus = cache.deja_collectes()
    maintenant = time.time()
    if not force:
        frais = [t for t in a_faire
                 if t in connus and maintenant - connus[t] < FRAICHEUR]
        a_faire = [t for t in a_faire if t not in set(frais)]
        if frais:
            print(f"{len(frais)} valeurs déjà fraîches, ignorées (--force pour les redemander)")

    print(f"{len(a_faire)} valeurs à collecter sur {len(places)} places\n")
    if not a_faire:
        return 0, []

    taux = fx.collecte(_devises())
    print(f"Taux de change : {len(taux)} devises ({', '.join(sorted(taux))})\n")

    # Deux registres d'échec, parce qu'ils appellent deux actions
    # différentes : `bloques` se relance, `inconnus` se corrige.
    faits, bloques, inconnus = [0], [], []

    def traiter(i_ticker):
        i, ticker = i_ticker
        # Départs échelonnés : quatre travailleurs qui partent ensemble
        # sur le premier lot suffisent à déclencher la limitation.
        time.sleep(PAUSE * (i % TRAVAILLEURS))
        societe, erreur = _collecte_une(ticker)

        with _verrou:
            faits[0] += 1
            n = faits[0]

        if societe:
            societe["place"] = index_place.get(ticker)
            societe["market_cap_eur"] = fx.en_euros(
                societe.get("market_cap"), societe.get("currency"), taux
            )
            cache.save_detail(societe)
            etat = f"{(societe['nom'] or '')[:32]:34} {societe.get('sector') or '—'}"
        elif erreur:
            bloques.append(ticker)
            etat = f"ÉCHEC — {erreur}"
        else:
            # Yahoo a répondu et ne connaît pas ce symbole : c'est une
            # absence réelle, pas un incident. Elle mérite d'être corrigée
            # dans data/universe.py plutôt que réessayée indéfiniment.
            inconnus.append(ticker)
            etat = "inconnu de Yahoo — symbole à corriger"

        print(f"[{n:4}/{len(a_faire)}] {ticker:14} {etat}", flush=True)

        # Réécriture périodique : le site profite de la collecte en cours.
        if n % PALIER == 0:
            with _verrou:
                _ecrire_index(taux)

    with cf.ThreadPoolExecutor(max_workers=TRAVAILLEURS) as ex:
        list(ex.map(traiter, enumerate(a_faire)))

    _ecrire_index(taux)
    return len(a_faire) - len(bloques) - len(inconnus), bloques, inconnus


# Ce que la lecture d'un bilan renseigne, et qu'une collecte de cours ne
# doit surtout pas effacer : les comptes ne se republient qu'une fois l'an.
CHAMPS_BILAN = (
    "total_debt", "cash_and_investments", "receivables", "total_assets",
    "bilan_date", "bilan_plan", "bilan_reserve", "bilan_source",
)


def _bilan_brvm(societe, relire):
    """Attache les comptes à une valeur d'Abidjan.

    Relus à la source si on le demande, repris du cache sinon. Un échec de
    lecture fait aussi retomber sur le cache : perdre un bilan déjà obtenu
    parce que la source a hoqueté aujourd'hui serait une régression que
    l'utilisateur verrait passer.
    """
    symbole = societe["ticker"].removesuffix(brvm.SUFFIXE)
    if relire:
        try:
            lu = brvm.bilan(symbole)
        except Exception as exc:
            print(f"  {symbole} : lecture impossible ({type(exc).__name__})")
            lu = None
        if lu:
            societe.update(lu)
            return True

    ancien = cache.detail(societe["ticker"]) or {}
    for champ in CHAMPS_BILAN:
        if ancien.get(champ) is not None:
            societe[champ] = ancien[champ]
    return False


def collecte_brvm(avec_bilans=False):
    """La cote de la BRVM, en une requête.

    Contrairement à Yahoo, la source publie sa cote entière sur une page :
    47 sociétés pour un aller-retour. On écrit les détails comme pour les
    autres places, de sorte que l'index se construit sans traitement
    particulier ensuite.

    Les **états financiers**, eux, se demandent fiche par fiche et ne
    changent qu'une fois l'an : ils ne sont relus que sur demande
    explicite, et seulement pour les sociétés dont le secteur n'a pas
    déjà tranché le verdict.
    """
    try:
        societes = brvm.societes()
    except Exception as exc:
        print(f"BRVM : collecte impossible ({type(exc).__name__}) — "
              f"on conserve la version en cache")
        return 0

    taux = fx.collecte(_devises())
    declares = set(brvm.tickers())
    nouveaux, lus, capitalisees = [], 0, 0
    for societe in societes:
        societe["place"] = "brvm"
        societe["market_cap_eur"] = fx.en_euros(
            societe.get("market_cap"), societe.get("currency"), taux
        )
        if societe.get("market_cap"):
            capitalisees += 1
        if _bilan_brvm(societe, avec_bilans):
            lus += 1
        cache.save_detail(societe)
        if societe["ticker"] not in declares:
            nouveaux.append(societe["ticker"])

    print(f"BRVM : {len(societes)} sociétés collectées, "
          f"{capitalisees} avec leur capitalisation")
    if avec_bilans:
        print(f"  {lus}/{len(brvm.FICHES)} bilans lus à la source")
    if nouveaux:
        print(f"  {len(nouveaux)} symboles nouveaux à déclarer dans data/brvm.py : "
              f"{', '.join(nouveaux)}")
    manquants = declares - {s["ticker"] for s in societes}
    if manquants:
        print(f"  {len(manquants)} déclarés mais absents de la cote : "
              f"{', '.join(sorted(manquants))}")
    return len(societes)


def _ecrire_index(taux, avec_metaux=False):
    """Réécrit l'index à partir de tous les détails présents sur disque.

    Les cours de l'or et de l'argent ne sont demandés qu'en fin de
    collecte : ils servent au nissab de la zakat, et deux requêtes de plus
    à chaque palier n'apporteraient rien.
    """
    societes = cache.charger_details(universe.tickers())
    cache.save_index(societes, taux, fx.metaux(taux) if avec_metaux else None)
    return len(societes)


def collecte_actus():
    """Le fil d'actualité, sur les plus grosses valeurs de l'univers."""
    valeurs, _, _ = cache.index()
    classees = sorted(
        [v for v in valeurs if v.get("market_cap_eur")],
        key=lambda v: -v["market_cap_eur"],
    )[:ACTUS_VALEURS]

    if not classees:
        print("Index vide : collectez d'abord les valeurs.")
        return []

    print(f"Actualités sur les {len(classees)} plus grosses valeurs\n")
    noms = {v["ticker"]: v["nom"] for v in classees}
    articles = []

    def traiter(i_valeur):
        i, valeur = i_valeur
        time.sleep(PAUSE * (i % TRAVAILLEURS))
        lot = yahoo.fetch_news(valeur["ticker"])
        for article in lot:
            article["valeur"] = noms.get(article["ticker"])
            article["place"] = valeur.get("place")
        with _verrou:
            articles.extend(lot)
            print(f"[{len(articles):4}] {valeur['ticker']:14} {len(lot)} article(s)", flush=True)

    with cf.ThreadPoolExecutor(max_workers=TRAVAILLEURS) as ex:
        list(ex.map(traiter, enumerate(classees)))

    # Dédoublonnage sur le lien : un même article est attaché à plusieurs
    # sociétés dès qu'il parle d'un secteur.
    uniques, vus = [], set()
    for article in sorted(articles, key=lambda a: a.get("publie") or "", reverse=True):
        if article["lien"] not in vus:
            vus.add(article["lien"])
            uniques.append(article)

    cache.save_actus(uniques)
    print(f"\n{len(uniques)} dépêches par valeur écrites")

    # Le fil francophone, qui ne dépend ni de l'univers ni de Yahoo.
    articles = presse.collecte()
    cache.save_presse(articles)
    illustres = sum(1 for a in articles if a.get("image"))
    print(f"{len(articles)} articles de presse francophone ({illustres} illustrés)")

    return uniques


def main():
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--force", action="store_true",
                         help="redemande même les valeurs déjà fraîches")
    parseur.add_argument("--places", default="",
                         help="places à collecter, séparées par des virgules")
    parseur.add_argument("--actus", action="store_true",
                         help="collecte seulement le fil d'actualité")
    parseur.add_argument("--index", action="store_true",
                         help="réécrit seulement l'index depuis le disque")
    parseur.add_argument("--brvm", action="store_true",
                         help="collecte seulement la cote de la BRVM")
    parseur.add_argument("--brvm-bilans", action="store_true",
                         help="relit aussi les états financiers de la BRVM")
    args = parseur.parse_args()

    if args.index:
        taux = fx.collecte(_devises())
        print(f"{_ecrire_index(taux, avec_metaux=True)} valeurs réécrites dans l'index")
        return 0

    if args.brvm or args.brvm_bilans:
        n = collecte_brvm(avec_bilans=args.brvm_bilans)
        if n:
            print(f"{_ecrire_index(fx.collecte(_devises()))} valeurs dans l'index")
        return 0 if n else 1

    if args.actus:
        return 0 if collecte_actus() else 1

    debut = time.time()
    reussies, bloques, inconnus = collecte_valeurs(
        _places_demandees(args.places), args.force
    )
    total = _ecrire_index(fx.collecte(_devises()), avec_metaux=True)

    duree = time.time() - debut
    print(f"\n{reussies} valeurs collectées en {duree / 60:.1f} min")
    print(f"{total} valeurs au total dans l'index")
    if bloques:
        print(f"\n{len(bloques)} bloquées par Yahoo — relancez `python refresh.py` "
              f"pour les reprendre :\n  {', '.join(bloques[:40])}"
              + (" …" if len(bloques) > 40 else ""))
    if inconnus:
        print(f"\n{len(inconnus)} symboles inconnus de Yahoo — à corriger dans "
              f"data/universe.py :\n  {', '.join(inconnus[:60])}"
              + (" …" if len(inconnus) > 60 else ""))

    collecte_actus()
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
