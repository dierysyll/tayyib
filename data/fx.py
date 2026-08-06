"""
Taux de change vers l'euro.

Dès qu'on sort d'Euronext, une capitalisation brute ne veut plus rien dire.
Bank Central Asia pèse 792 552 milliards — de roupies indonésiennes, soit
environ 45 milliards d'euros. Trier l'univers sur ce nombre placerait
Jakarta au-dessus d'Apple, et comparer un ratio de taille entre deux places
n'aurait aucun sens.

On convertit donc toute capitalisation en euros, et c'est cette valeur
convertie qui sert au tri et aux classements. Le montant d'origine est
conservé et affiché avec sa devise : c'est celui que l'utilisateur
retrouvera chez son courtier.

Ce que la conversion ne touche pas
----------------------------------
Les **ratios de screening** ne sont pas convertis, et n'ont pas à l'être :
dette et capitalisation d'une même société sont dans la même devise, le
rapport est donc invariant. Un taux de change erroné fausserait l'ordre
d'affichage, jamais un verdict.

Le cas de Londres
-----------------
Yahoo cote le London Stock Exchange en **pence** (`GBp`), pas en livres.
Un oubli ici divise ou multiplie par cent la taille des valeurs
britanniques — c'est l'erreur classique sur cette place, et elle est
silencieuse.
"""

import yfinance as yf

# Devises exprimées en sous-unité chez Yahoo : le montant doit d'abord être
# ramené à l'unité principale avant conversion.
SOUS_UNITES = {
    "GBp": ("GBP", 100.0),   # pence → livre
    "ZAc": ("ZAR", 100.0),   # cent sud-africain → rand
    "ILA": ("ILS", 100.0),   # agora → shekel
}


def _paire(devise):
    """Le symbole Yahoo du taux EUR → devise (ex. EURUSD=X)."""
    return f"EUR{devise}=X"


def collecte(devises):
    """Récupère les taux EUR → devise pour les devises demandées.

    Renvoie un dictionnaire {devise: unités par euro}. L'euro vaut 1 par
    construction. Une devise dont le taux est introuvable est absente du
    résultat : `en_euros` renverra alors None plutôt qu'un montant faux.
    """
    taux = {"EUR": 1.0}

    besoins = set()
    for devise in devises:
        principale, _ = SOUS_UNITES.get(devise, (devise, 1.0))
        besoins.add(principale)
    besoins.discard("EUR")

    for devise in sorted(besoins):
        try:
            histo = yf.Ticker(_paire(devise)).history(period="5d")
        except Exception:
            continue
        if histo is None or histo.empty:
            continue
        valeur = float(histo["Close"].iloc[-1])
        if valeur > 0:
            taux[devise] = valeur

    return taux


# --- Or et argent ---------------------------------------------------------
#
# Le nissab — le seuil au-delà duquel la zakat est due — n'est pas un
# montant mais un poids : 85 g d'or, ou 595 g d'argent. Sa contrepartie en
# euros change donc tous les jours, et un chiffre figé dans le code serait
# faux dès le lendemain.
#
# Les deux poids ne donnent pas le même seuil, et l'écart n'est pas
# marginal : l'argent place la barre bien plus bas, donc rend la zakat due
# à beaucoup plus de gens. Les écoles divergent sur celui qu'il faut
# retenir. On calcule les deux et on laisse l'utilisateur trancher — ce
# n'est pas à un screener de choisir son école.

ONCE_TROY_EN_GRAMMES = 31.1034768

NISSAB_OR_G = 85.0
NISSAB_ARGENT_G = 595.0


def metaux(taux):
    """Prix du gramme d'or et d'argent en euros, et nissab correspondant.

    Renvoie None si la cotation n'est pas disponible : la page Zakat
    demande alors le prix à l'utilisateur plutôt que d'afficher un seuil
    inventé.
    """
    resultat = {}

    for cle, symbole in (("or", "GC=F"), ("argent", "SI=F")):
        try:
            histo = yf.Ticker(symbole).history(period="5d")
        except Exception:
            continue
        if histo is None or histo.empty:
            continue

        # Les contrats à terme sont cotés en dollars par once troy.
        once_usd = float(histo["Close"].iloc[-1])
        gramme_eur = en_euros(once_usd / ONCE_TROY_EN_GRAMMES, "USD", taux)
        if gramme_eur:
            resultat[cle] = round(gramme_eur, 4)

    if "or" in resultat:
        resultat["nissab_or"] = round(resultat["or"] * NISSAB_OR_G, 2)
    if "argent" in resultat:
        resultat["nissab_argent"] = round(resultat["argent"] * NISSAB_ARGENT_G, 2)

    return resultat or None


def en_euros(montant, devise, taux):
    """Convertit un montant vers l'euro. None si le taux manque.

    On préfère renvoyer None plutôt qu'un montant approché : une valeur
    absente s'affiche « — », alors qu'un montant faux se compare et se
    trie comme s'il était juste.
    """
    if montant is None or not devise:
        return None

    principale, diviseur = SOUS_UNITES.get(devise, (devise, 1.0))
    taux_devise = taux.get(principale)
    if not taux_devise:
        return None

    return (montant / diviseur) / taux_devise
