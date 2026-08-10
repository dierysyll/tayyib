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

Deux collectes, à deux rythmes
------------------------------
Les **cours** viennent de la page de cotation : une requête pour la cote
entière, et elle vaut d'être rejouée chaque jour.

Les **états financiers** viennent d'ailleurs — une fiche de documents par
société, où l'émetteur dépose ses comptes en PDF. Ils ne changent qu'une
fois l'an, et les redemander quotidiennement serait aussi inutile que
malpoli envers la source. `data/bilans.py` en tire les quatre grandeurs
du screening ; ce module se charge de trouver le bon document.

Où trouver la capitalisation
----------------------------
Les fiches émetteurs publient un nombre d'actions arrêté en 2015, qu'il
serait imprudent d'utiliser — nous en avions d'abord conclu que la
capitalisation était hors d'atteinte, et que la moitié des standards ne
pourraient jamais conclure sur cette place. C'était faux : la BRVM tient
une page de capitalisations à jour, qui donne pour chaque société son
nombre de titres, son cours et sa capitalisation globale. Les trois
grandeurs sont cohérentes entre elles au franc près sur les 47 valeurs,
ce que `capitalisations()` revérifie à chaque collecte.

Avec elle, les six standards concluent ici comme ailleurs : ceux qui
divisent par la capitalisation boursière — AAOIFI, Dow Jones, S&P
Shariah — comme ceux qui divisent par le total du bilan.

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
import os
import re
import urllib.request

from data import bilans, cache

COTATIONS = "https://www.brvm.org/fr/cours-actions/0"
CAPITALISATIONS = "https://www.brvm.org/fr/capitalisations/0"
FICHE = "https://www.brvm.org/fr/rapports-societe-cotes/"

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

# Symbole → (fiche de documents sur brvm.org, motif attendu dans l'intitulé).
#
# Le motif n'est pas une précaution théorique. La BRVM dépose parfois un
# document sur la mauvaise fiche : celle de CFAO Motors porte des états
# financiers de Tractafric, qui est une autre société de la cote. Prendre
# le document le plus récent d'une fiche attribuerait le bilan de l'une à
# l'autre — une erreur invisible et grave. L'intitulé fait donc foi, et
# un document qui ne nomme pas la société attendue est ignoré.
#
# Les banques et les autres activités que le filtre sectoriel écarte n'y
# figurent pas : leur verdict est acquis sans comptes, et les demander
# serait solliciter la source pour rien.
FICHES = {
    "SNTS":  ("sonatel", r"sonatel"),
    "ORAC":  ("orange-ci", r"orange"),
    "ONTBF": ("onatel-bf", r"onatel"),
    "CIEC":  ("cie-ci", r"\bcie\b"),
    "SDCC":  ("sodeci", r"sodeci"),
    "PALC":  ("palm-ci", r"\bpalm\b"),
    "SOGC":  ("sogb", r"\bsogb\b"),
    "SPHC":  ("saph-ci", r"\bsaph\b"),
    "SCRC":  ("sucrivoire", r"sucrivoire"),
    "SICC":  ("sicor", r"sicor"),
    "NTLC":  ("nestle-ci", r"nestle"),
    "UNLC":  ("unilever-ci", r"unilever"),
    "SHEC":  ("vivo-energy-ci", r"vivo"),
    "TTLC":  ("total", r"marketing[ _]ci\b"),
    "TTLS":  ("total-senegal-sa", r"marketing[ _]sn\b|total[ _]senegal"),
    "SIVC":  ("air-liquide-ci", r"erium|air[ _]liquide"),
    "CABC":  ("sicable", r"sicable"),
    "FTSC":  ("filtisac-ci", r"filtisac"),
    "SEMC":  ("crown-siem-ci", r"eviosys|siem"),
    "SMBC":  ("smb", r"\bsmb\b"),
    "UNXC":  ("uniwax-ci", r"uniwax"),
    "STAC":  ("setao-ci", r"setao"),
    "BNBC":  ("bernabe-ci", r"bernabe"),
    "CFAC":  ("cfao-motors-ci", r"cfao"),
    "PRSC":  ("tractafric-ci", r"tractafric"),
    "SDSC":  ("bollore-transport-logistics", r"africa[ _]global[ _]logistics|\bagl\b|bollore"),
    "ABJC":  ("servair-abidjan-ci", r"servair"),
    "NEIC":  ("nei-ceda-ci", r"nei[ _]?ceda"),
}

BALISES = re.compile(r"<[^>]+>")
ETATS_FINANCIERS = re.compile(r"[ée]tats?\s+financiers", re.I)
EXERCICE = re.compile(r"exercices?\s*(?:\d{4}\s*(?:à|-|a)\s*)?(\d{4})", re.I)

# Les PDF ne changent qu'une fois l'an : les garder sur disque évite de
# redemander vingt méga-octets à la source à chaque collecte.
DOSSIER_PDF = os.path.join(cache.CACHE_DIR, "brvm")


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


def _cellules(tableau):
    """Les lignes d'un tableau HTML, cellules nettoyées, en-tête écarté."""
    for tr in re.findall(r"<tr.*?</tr>", tableau, re.S)[1:]:
        cellules = [
            re.sub(r"\s+", " ", html.unescape(BALISES.sub(" ", c))).strip()
            for c in re.findall(r"<td.*?</td>", tr, re.S)
        ]
        cellules = [c for c in cellules if c]
        if cellules:
            yield cellules


def capitalisations():
    """Nombre de titres et capitalisation boursière, par symbole.

    La page des capitalisations publie les deux, ainsi que le cours qui les
    relie. Nous vérifions que le produit retombe sur le total annoncé et
    écartons la ligne sinon : trois grandeurs liées par une multiplication
    forment un contrôle gratuit, et une capitalisation fausse déplacerait
    silencieusement le verdict des standards qui divisent par elle.
    """
    requete = urllib.request.Request(CAPITALISATIONS, headers=ENTETES)
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        page = reponse.read().decode("utf-8", "ignore")

    tableaux = [t for t in re.findall(r"<table.*?</table>", page, re.S)
                if "Nombre de titres" in t]
    if not tableaux:
        return {}

    resultat = {}
    for cellules in _cellules(tableaux[0]):
        if len(cellules) < 6:
            continue
        symbole = cellules[0].strip().upper()
        titres, cours = _nombre(cellules[2]), _nombre(cellules[3])
        capitalisation = _nombre(cellules[5])
        if not (titres and cours and capitalisation):
            continue
        if abs(titres * cours - capitalisation) > max(1, capitalisation * 1e-6):
            continue
        resultat[symbole] = {"actions": titres, "market_cap": capitalisation}
    return resultat


def societes():
    """Toutes les sociétés cotées, au format du reste de l'application.

    Le dictionnaire produit est celui de `data/yahoo.py`. Les postes de
    bilan restent à None ici : ils viennent des états financiers, que
    `bilan()` lit à la demande et que la collecte attache ensuite.

    Deux requêtes : la cote pour les cours, la page des capitalisations
    pour le nombre de titres. Si la seconde échoue, les cours sont servis
    quand même — une capitalisation manquante coûte trois standards sur
    six, une cote manquante coûte la place entière.
    """
    try:
        capis = capitalisations()
    except Exception:
        capis = {}

    resultat = []
    for ligne in cotations():
        secteur, industrie, pays = SOCIETES.get(
            ligne["symbole"], (None, None, None)
        )
        capi = capis.get(ligne["symbole"], {})
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
            "market_cap": capi.get("market_cap"),
            "dividende_par_action": None,
            "rendement": None,
            "site": None,
            "resume": None,
            # Le nombre de titres se déduit ailleurs de la capitalisation
            # divisée par le cours ; on le conserve tel que la source le
            # publie, puisqu'ici il est donné et non reconstitué.
            "valorisation": {"actions": capi.get("actions")} if capi else {},
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


def _sans_accents(texte):
    """Un intitulé comparable : sans accents, sans casse, sans ponctuation.

    Les émetteurs écrivent « CÔTE D'IVOIRE », « Côte d'Ivoire » ou
    « COTE D IVOIRE » selon l'humeur du jour ; le motif attendu ne doit
    pas en dépendre.
    """
    table = str.maketrans("àâäçéèêëîïôöùûüÀÂÄÇÉÈÊËÎÏÔÖÙÛÜ",
                          "aaaceeeeiioouuuAAACEEEEIIOOUUU")
    return re.sub(r"[^a-z0-9]+", " ", texte.translate(table).lower())


def _documents(slug):
    """Les états financiers déposés sur une fiche, du plus récent au plus ancien.

    Chaque entrée est (année de l'exercice, intitulé normalisé, adresse).
    Les rapports d'activité, communiqués et rapports RSE sont écartés :
    seuls les états financiers portent un bilan.
    """
    requete = urllib.request.Request(FICHE + slug, headers=ENTETES)
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        page = reponse.read().decode("utf-8", "ignore")

    trouves = []
    for tr in re.findall(r"<tr.*?</tr>", page[page.find("<body"):], re.S):
        lien = re.search(r'href="([^"]*\.pdf[^"]*)"', tr, re.I)
        if not lien:
            continue
        intitule = re.sub(r"\s+", " ", html.unescape(BALISES.sub(" ", tr))).strip()
        if not ETATS_FINANCIERS.search(intitule):
            continue
        adresse = html.unescape(lien.group(1))
        repere = _sans_accents(intitule + " " + adresse.replace("_", " "))
        annees = EXERCICE.findall(repere)
        if not annees:
            continue
        trouves.append((int(annees[0]), repere, adresse))
    return sorted(trouves, reverse=True)


def _telecharger(adresse):
    """Le PDF, depuis le disque s'il y est déjà, depuis la source sinon."""
    os.makedirs(DOSSIER_PDF, exist_ok=True)
    chemin = os.path.join(DOSSIER_PDF, adresse.rsplit("/", 1)[-1][:120])
    if os.path.exists(chemin):
        with open(chemin, "rb") as fichier:
            return fichier.read()

    requete = urllib.request.Request(adresse, headers=ENTETES)
    with urllib.request.urlopen(requete, timeout=120) as reponse:
        contenu = reponse.read()
    with open(chemin, "wb") as fichier:
        fichier.write(contenu)
    return contenu


def bilan(symbole):
    """Le dernier bilan publié par une société de la cote, ou None.

    On essaie les documents du plus récent au plus ancien, et l'on
    s'arrête au premier dont `data/bilans.py` accepte de lire le bilan :
    la BRVM publie sous l'intitulé « états financiers » des communiqués
    de résultats qui n'en contiennent aucun, et il serait dommage de
    renoncer à l'exercice précédent pour cette raison.
    """
    fiche = FICHES.get(symbole)
    if not fiche:
        return None
    slug, motif = fiche

    for annee, repere, adresse in _documents(slug):
        if not re.search(motif, repere):
            continue
        contenu = _telecharger(adresse)
        try:
            lu = bilans.lire(contenu, exercice=annee)
        except Exception:
            # Un PDF illisible n'est pas une panne : on passe au suivant.
            continue
        # Un total d'actif sans aucun poste ne permet de calculer aucun
        # ratio. Autant continuer de chercher : mieux vaut le bilan de
        # l'an dernier, complet, qu'un total isolé de cette année.
        if lu and any(lu[cle] is not None for cle in
                      ("total_debt", "cash_and_investments", "receivables")):
            lu["bilan_source"] = adresse
            return lu
    return None
