"""
La BRVM d'Abidjan, collectée à la source.

Pourquoi un collecteur à part
------------------------------
La BRVM est la place commune aux huit pays de l'UEMOA — Bénin, Burkina
Faso, Côte d'Ivoire, Guinée-Bissau, Mali, Niger, Sénégal, Togo. C'est,
de très loin, la place la plus utile au lecteur de ce produit : un
épargnant sénégalais ou ivoirien y trouve les seules actions qu'il puisse
acheter dans sa propre monnaie, sans compte à l'étranger.

Yahoo Finance ne la connaît pas. Pas « mal », pas « partiellement » :
aucun symbole BRVM n'y existe. Nous étions donc un screener francophone
qui ne couvrait pas l'Afrique francophone — l'exact contraire de ce que
le produit prétend faire.

La BRVM publie elle-même ses cotations. Ce module les lit à sa source,
et produit des sociétés au même format que `data/yahoo.py`, de sorte que
le moteur de screening, le cache et l'interface ne changent pas d'un
caractère.

Ce que ce module ne fait pas encore
-----------------------------------
Il ne lit que les **cours**. Les états financiers existent — la BRVM
publie les PDF au plan SYSCOHADA, avec des codes de poste normalisés qui
les rendent extractibles — mais c'est un autre chantier. En attendant,
les valeurs arrivent sans bilan, donc sans ratios calculables.

Ce n'est pas un demi-produit : le **filtre sectoriel**, lui, s'applique
pleinement. Les seize banques de la cote sont exclues sans qu'aucun bilan
soit nécessaire, comme la loterie du Bénin, la brasserie et le
cigarettier. Pour le reste, le verdict est « à vérifier », et c'est la
réponse honnête tant que les comptes ne sont pas lus.

Sur la classification sectorielle
---------------------------------
Yahoo fournit un secteur pour ses valeurs ; ici, personne ne le fournit.
Les activités ci-dessous sont donc **renseignées à la main**, à partir de
l'activité connue et publique de chaque société. C'est une intervention
humaine, elle est signalée comme telle, et elle emploie exactement le
vocabulaire de Yahoo pour que `screening/sectors.py` s'applique sans
traitement particulier — une banque ivoirienne doit être exclue par la
même règle qu'une banque française.
"""

import html
import re
import urllib.request

COTATIONS = "https://www.brvm.org/fr/cours-actions/0"

ENTETES = {
    "User-Agent": "Mozilla/5.0 (compatible; Tayyib/1.0; +https://tayyib.app)",
    "Accept": "text/html,application/xhtml+xml",
}

# Le suffixe distingue nos symboles de ceux de Yahoo. `SNTS` seul risquerait
# de heurter un symbole américain un jour ; `SNTS.BRVM` jamais.
SUFFIXE = ".BRVM"

# Symbole → activité, renseignée à la main (voir l'en-tête du module).
# Le pays est celui du siège, la BRVM étant commune à huit États.
SOCIETES = {
    # --- Banques et finance : exclues par le filtre sectoriel -----------
    "BICB":  ("Financial Services", "Banks - Regional", "Bénin"),
    "BICC":  ("Financial Services", "Banks - Regional", "Côte d'Ivoire"),
    "BOAB":  ("Financial Services", "Banks - Regional", "Bénin"),
    "BOABF": ("Financial Services", "Banks - Regional", "Burkina Faso"),
    "BOAC":  ("Financial Services", "Banks - Regional", "Côte d'Ivoire"),
    "BOAM":  ("Financial Services", "Banks - Regional", "Mali"),
    "BOAN":  ("Financial Services", "Banks - Regional", "Niger"),
    "BOAS":  ("Financial Services", "Banks - Regional", "Sénégal"),
    "CBIBF": ("Financial Services", "Banks - Regional", "Burkina Faso"),
    "ECOC":  ("Financial Services", "Banks - Regional", "Côte d'Ivoire"),
    "ETIT":  ("Financial Services", "Banks - Diversified", "Togo"),
    "NSBC":  ("Financial Services", "Banks - Regional", "Côte d'Ivoire"),
    "ORGT":  ("Financial Services", "Banks - Regional", "Togo"),
    "SGBC":  ("Financial Services", "Banks - Regional", "Côte d'Ivoire"),
    "SIBC":  ("Financial Services", "Banks - Regional", "Côte d'Ivoire"),
    "SAFC":  ("Financial Services", "Credit Services", "Côte d'Ivoire"),

    # --- Autres activités exclues sans examen des comptes ---------------
    "LNBB":  ("Consumer Cyclical", "Gambling", "Bénin"),
    "SLBC":  ("Consumer Defensive", "Beverages - Brewers", "Côte d'Ivoire"),
    "STBC":  ("Consumer Defensive", "Tobacco", "Côte d'Ivoire"),

    # --- Télécommunications ---------------------------------------------
    "SNTS":  ("Communication Services", "Telecom Services", "Sénégal"),
    "ORAC":  ("Communication Services", "Telecom Services", "Côte d'Ivoire"),
    "ONTBF": ("Communication Services", "Telecom Services", "Burkina Faso"),

    # --- Services aux collectivités -------------------------------------
    "CIEC":  ("Utilities", "Utilities - Regulated Electric", "Côte d'Ivoire"),
    "SDCC":  ("Utilities", "Utilities - Regulated Water", "Côte d'Ivoire"),

    # --- Agro-industrie --------------------------------------------------
    "PALC":  ("Consumer Defensive", "Farm Products", "Côte d'Ivoire"),
    "SOGC":  ("Basic Materials", "Agricultural Inputs", "Côte d'Ivoire"),
    "SPHC":  ("Basic Materials", "Agricultural Inputs", "Côte d'Ivoire"),
    "SCRC":  ("Consumer Defensive", "Confectioners", "Côte d'Ivoire"),
    "SICC":  ("Consumer Defensive", "Farm Products", "Côte d'Ivoire"),
    "NTLC":  ("Consumer Defensive", "Packaged Foods", "Côte d'Ivoire"),
    "UNLC":  ("Consumer Defensive", "Household & Personal Products", "Côte d'Ivoire"),

    # --- Énergie et distribution ----------------------------------------
    "SHEC":  ("Energy", "Oil & Gas Refining & Marketing", "Côte d'Ivoire"),
    "TTLC":  ("Energy", "Oil & Gas Refining & Marketing", "Côte d'Ivoire"),
    "TTLS":  ("Energy", "Oil & Gas Refining & Marketing", "Sénégal"),

    # --- Industrie et matériaux ------------------------------------------
    "SIVC":  ("Basic Materials", "Specialty Chemicals", "Côte d'Ivoire"),
    "CABC":  ("Industrials", "Electrical Equipment & Parts", "Côte d'Ivoire"),
    "FTSC":  ("Consumer Cyclical", "Packaging & Containers", "Côte d'Ivoire"),
    "SEMC":  ("Consumer Cyclical", "Packaging & Containers", "Côte d'Ivoire"),
    "SMBC":  ("Basic Materials", "Steel", "Côte d'Ivoire"),
    "UNXC":  ("Consumer Cyclical", "Textile Manufacturing", "Côte d'Ivoire"),
    "STAC":  ("Industrials", "Engineering & Construction", "Côte d'Ivoire"),
    "BNBC":  ("Industrials", "Industrial Distribution", "Côte d'Ivoire"),

    # --- Automobile, transport, services ---------------------------------
    "CFAC":  ("Consumer Cyclical", "Auto & Truck Dealerships", "Côte d'Ivoire"),
    "PRSC":  ("Consumer Cyclical", "Auto & Truck Dealerships", "Côte d'Ivoire"),
    "SDSC":  ("Industrials", "Integrated Freight & Logistics", "Côte d'Ivoire"),
    "ABJC":  ("Consumer Cyclical", "Restaurants", "Côte d'Ivoire"),
    "NEIC":  ("Communication Services", "Publishing", "Côte d'Ivoire"),
}

BALISES = re.compile(r"<[^>]+>")


def _nombre(texte):
    """Un montant de la BRVM — « 3 010 », « 7,50 » — en flottant.

    Espaces insécables comme séparateurs de milliers, virgule décimale :
    le format est francophone, et `float()` s'y casserait les dents.
    """
    if not texte:
        return None
    propre = (texte.replace(" ", "").replace(" ", "")
                   .replace(" ", "").replace(",", "."))
    try:
        return float(propre)
    except ValueError:
        return None


def cotations():
    """La cote du jour, telle que la BRVM la publie.

    Renvoie une liste de dictionnaires bruts : symbole, nom, volume, cours
    de clôture et variation. Lève l'exception réseau telle quelle —
    l'appelant décide s'il abandonne ou s'il conserve la version en cache.
    """
    requete = urllib.request.Request(COTATIONS, headers=ENTETES)
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        page = reponse.read().decode("utf-8", "ignore")

    tableaux = [t for t in re.findall(r"<table.*?</table>", page, re.S)
                if "Symbole" in t]
    if not tableaux:
        return []

    lignes = []
    for tr in re.findall(r"<tr.*?</tr>", tableaux[0], re.S)[1:]:
        cellules = [
            re.sub(r"\s+", " ", html.unescape(BALISES.sub(" ", c))).strip()
            for c in re.findall(r"<td.*?</td>", tr, re.S)
        ]
        cellules = [c for c in cellules if c]
        if len(cellules) < 7:
            continue
        symbole, nom, volume, veille, ouverture, cloture, variation = cellules[:7]
        lignes.append({
            "symbole": symbole.strip().upper(),
            "nom": nom.strip(),
            "volume": _nombre(volume),
            "cloture_precedente": _nombre(veille),
            "prix": _nombre(cloture),
            # La BRVM publie la variation en pourcentage ; nous la stockons
            # en fraction, comme celle de Yahoo.
            "variation": (_nombre(variation) / 100
                          if _nombre(variation) is not None else None),
        })
    return lignes


def societes():
    """Toutes les sociétés cotées, au format du reste de l'application.

    Le dictionnaire produit est celui de `data/yahoo.py`, aux champs de
    bilan près : ils restent à None tant que l'extracteur SYSCOHADA
    n'existe pas, et le moteur conclut alors « à vérifier » — sauf pour
    les activités que le filtre sectoriel écarte d'emblée.
    """
    resultat = []
    for ligne in cotations():
        secteur, industrie, pays = SOCIETES.get(
            ligne["symbole"], (None, None, None)
        )
        resultat.append({
            "ticker": ligne["symbole"] + SUFFIXE,
            "nom": ligne["nom"].title(),
            "sector": secteur,
            "industry": industrie,
            "currency": "XOF",
            "pays": pays,
            "prix": ligne["prix"],
            "cloture_precedente": ligne["cloture_precedente"],
            "variation": ligne["variation"],
            "volume": ligne["volume"],
            # Sans nombre d'actions publié, la capitalisation reste inconnue :
            # les standards qui divisent par elle ne pourront pas conclure.
            "market_cap": None,
            "dividende_par_action": None,
            "rendement": None,
            "site": None,
            "resume": None,
            "valorisation": {},
            "total_debt": None,
            "cash_and_investments": None,
            "receivables": None,
            "total_assets": None,
            "bilan_date": None,
            "historique": [],
            "cours": [],
            "dividendes": [],
        })
    return resultat


def tickers():
    """Les symboles déclarés, suffixés — l'univers que nous prétendons couvrir."""
    return [s + SUFFIXE for s in SOCIETES]
