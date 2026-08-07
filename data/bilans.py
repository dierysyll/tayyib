"""
Lire un bilan dans un PDF publié par la BRVM.

Pourquoi ce module existe
-------------------------
`data/brvm.py` collecte les cours d'Abidjan, mais pas les comptes : les
valeurs arrivaient donc sans bilan, et le moteur ne pouvait conclure que
« à vérifier » partout où le secteur ne tranchait pas. Ce module lit les
comptes eux-mêmes, et ce sont les seuls chiffres qui permettent un
verdict motivé.

Les émetteurs de l'UEMOA déposent leurs états financiers auprès de la
BRVM, en PDF, une fiche par société. Ces PDF ont une couche texte — ils
sont produits par un tableur, pas scannés — donc ils sont lisibles sans
reconnaissance de caractères.

Trois présentations, pas une
----------------------------
Le plan comptable de la zone est le **SYSCOHADA révisé**, et il apparaît
sous deux formes :

  - *complète* — chaque poste porte son code normalisé : BZ pour le total
    du bilan, BT pour la trésorerie-actif, BI pour les clients, DA pour
    les emprunts. C'est la forme la plus sûre, le code ne dépendant ni de
    l'orthographe du libellé ni de sa casse.
  - *condensée* — les agrégats seuls, repérés par leur libellé
    (« TOTAL ACTIF », « Trésorerie - actif »). C'est ce que publient les
    sociétés qui ne déposent qu'une synthèse.

S'y ajoutent les quelques groupes qui consolident en **IFRS** — Sonatel
au premier chef, et c'est la valeur la plus détenue de la place. Les
ignorer aurait vidé l'exercice de son intérêt, donc leur présentation est
lue aussi.

Le piège de la colonne, et comment on l'évite
---------------------------------------------
L'actif SYSCOHADA se présente en trois colonnes : BRUT, AMORTISSEMENTS,
NET. Chez Erium, la ligne du total porte 25,4 Md, 10,8 Md et 14,6 Md. Le
total du bilan est le **net** — prendre la première colonne surestimerait
l'actif de 74 %, donc sous-estimerait tous les ratios, donc déclarerait
conformes des sociétés qui ne le sont pas. Une erreur silencieuse, et du
mauvais côté.

Nous ne devinons pas la colonne : nous utilisons l'identité comptable.
Le total de l'actif est égal au total du passif, et le passif n'a qu'une
colonne de montants. La colonne de l'actif retenue est donc celle qui
**égale le passif** ; s'il n'y en a aucune, le document est refusé plutôt
que lu de travers. La même vérification attrape au passage une page mal
appariée, un nombre mal découpé ou un poste mal identifié.

Le découpage des nombres
------------------------
« TOTAL ACTIF 199 116 293 202 603 319 » porte deux montants de neuf
chiffres, séparés comme les milliers le sont eux-mêmes : par une espace.
Aucune expression régulière ne peut trancher. Nous lisons donc la
**position** de chaque groupe de chiffres sur la page : à l'intérieur
d'un montant l'écart ne dépasse pas 0,65 largeur de caractère, entre deux
colonnes il ne descend pas sous 3,0 — mesuré sur les documents de la
cote, l'histogramme est vide entre les deux. Le seuil est posé au milieu.

Ce que « dette » veut dire ici
------------------------------
`total_debt` correspond à ce que Yahoo appelle *Total Debt*, pour que les
ratios d'Abidjan soient comparables à ceux des autres places : les
emprunts, les dettes de location-acquisition et les crédits bancaires de
trésorerie. En SYSCOHADA, DA + DB + DT. Les découverts bancaires en font
partie : ce sont des concours rémunérés, et les omettre ferait passer
Erium de 39,5 % à 27,8 % de dette rapportée au bilan, c'est-à-dire de non
conforme à conforme.
"""

import io
import re

import pdfplumber

# Les codes de poste du SYSCOHADA révisé dont nous avons besoin.
CODES_ACTIF = {
    "total_assets": ("BZ",),
    "cash_and_investments": ("BT",),
    "receivables": ("BI",),
}
CODES_PASSIF = {
    "total_passif": ("DZ",),
    "total_debt": ("DA", "DB", "DT"),
}

# La forme condensée : les mêmes grandeurs, repérées par leur libellé.
# `receivables` y est le poste BG « créances et emplois assimilés », plus
# large que les seuls clients — voir `APPROXIMATIONS`.
#
# Les mêmes libellés servent de total des deux côtés, et ce n'est pas une
# négligence. La moitié des émetteurs imprime l'actif et le passif en
# vis-à-vis, sous un seul intitulé : la ligne « TOTAL ACTIF » de Filtisac
# porte quatre montants, l'actif de deux exercices puis le passif des
# mêmes. Le libellé ne dit donc pas de quel côté on est ; c'est la colonne
# qui le dit, et `_accorder` la désigne en exigeant que les deux montants
# viennent de deux cellules distinctes.
TOTAUX = (r"TOTAL\s+ACTIF", r"TOTAL\s+PASSIF", r"TOTAL\s+G[EÉ]N[EÉ]RAL", r"TOTAL")
LIBELLES_ACTIF = {
    "total_assets": TOTAUX,
    "cash_and_investments": (r"(TOTAL\s+)?TR[EÉ]SORERIE\s*[-–]?\s*ACTIF",),
    "receivables": (r"(TOTAL\s+)?CR[EÉ]ANCES\s+ET\s+EMPLOIS\s+ASSIMIL[EÉ]S",),
}
LIBELLES_PASSIF = {
    "total_passif": TOTAUX,
    # « Autres dettes financières » est le libellé que retiennent les
    # sociétés qui présentent leur passif sans le total SYSCOHADA ;
    # « TOTAL DETTES FINANCIÈRES… » celui des présentations complètes qui
    # impriment les intitulés sans les codes de poste.
    "total_debt": (
        r"(TOTAL\s+)?(EMPRUNTS?\s*(&|ET)\s*)?(AUTRES\s+)?DETTES\s+FINANCI[EÈ]RES"
        r"(\s+ET\s+RESSOURCES\s+ASSIMIL[EÉ]ES|\s+DIVERSES)?",
        r"(TOTAL\s+)?TR[EÉ]SORERIE\s*[-–]?\s*PASSIF",
    ),
}

# La présentation IFRS des groupes consolidés.
LIBELLES_IFRS_ACTIF = {
    "total_assets": (r"TOTAL\s+DE\s+L.ACTIF$",),
    "cash_and_investments": (r"DISPONIBILIT[EÉ]S\s+ET\s+QUASI[\s-]?DISPONIBILIT[EÉ]S$",),
    "receivables": (r"CR[EÉ]ANCES\s+CLIENTS$",),
}
LIBELLES_IFRS_PASSIF = {
    "total_passif": (r"TOTAL\s+DU\s+PASSIF\s+ET\s+DES\s+CAPITAUX\s+PROPRES$",),
    "total_debt": (
        r"PASSIFS\s+FINANCIERS\s+(NON\s+)?COURANTS$",
        r"DETTES\s+LOCATIVES\s+(NON\s+)?COURANTES$",
    ),
}

# Les plans sont essayés dans cet ordre : le plus explicite d'abord.
PLANS = (
    ("syscohada", CODES_ACTIF, CODES_PASSIF, True),
    ("syscohada-condense", LIBELLES_ACTIF, LIBELLES_PASSIF, False),
    ("ifrs", LIBELLES_IFRS_ACTIF, LIBELLES_IFRS_PASSIF, False),
)

LIBELLES_PLANS = {
    "syscohada": "SYSCOHADA, présentation complète",
    "syscohada-condense": "SYSCOHADA, présentation condensée",
    "ifrs": "IFRS, comptes consolidés",
}

# Ce que la présentation condensée ne permet pas de lire exactement. Les
# deux écarts vont dans le sens prudent : ils gonflent le numérateur, donc
# le ratio, donc ils peuvent refuser une société conforme mais jamais en
# déclarer une qui ne l'est pas.
APPROXIMATIONS = {
    "syscohada-condense": (
        "La présentation condensée ne détaille pas les postes : les créances "
        "retenues sont l'ensemble « créances et emplois assimilés », plus "
        "large que les seuls clients, et la dette inclut les provisions pour "
        "risques, que le bilan complet isolerait. Les deux écarts majorent "
        "les ratios : ils peuvent écarter une société conforme, jamais "
        "retenir une société qui ne l'est pas."
    ),
}

UNITES = (
    (1_000_000, re.compile(r"en\s+millions?\s+(de\s+)?(F\s*CFA|FRANCS)", re.I)),
    (1_000, re.compile(r"en\s+milliers?\s+(de\s+)?(F\s*CFA|FRANCS)", re.I)),
)

JETON = re.compile(r"^\(?-?[\d,]+\)?$")
DATE_BILAN = re.compile(r"\b31[/\-. ]?(?:12|d[ée]c\w*)[/\-. ]?(\d{4})\b", re.I)

# Deux montants sont « les mêmes » à un franc près : l'actif et le passif
# sont parfois arrondis d'une unité l'un par rapport à l'autre.
TOLERANCE = 1e-4

# En deçà, le total d'un bilan n'est pas crédible pour une société cotée :
# c'est le signe d'une unité mal lue ou d'une ligne mal identifiée.
PLANCHER_BILAN = 1e8


def _valeur(texte):
    """Un montant, quelle que soit la convention d'écriture.

    Les parenthèses valent le signe moins — c'est la convention des
    présentations IFRS.

    La virgule, elle, veut dire deux choses opposées sur cette cote :
    Nestlé écrit « 48,140,912,196 » à l'anglaise, Orange écrit « 20,8 »
    à la française. Les confondre transformerait 20,8 millions en 208.
    Ce qui les distingue est la taille des groupes : un séparateur de
    milliers en découpe toujours de trois chiffres exactement.
    """
    negatif = texte.startswith("(") and texte.endswith(")")
    brut = texte.strip("()").replace(" ", "").replace(" ", "")
    if "," in brut:
        tete, *groupes = brut.split(",")
        if groupes and all(len(g) == 3 for g in groupes):
            brut = tete + "".join(groupes)
        elif len(groupes) == 1:
            brut = tete + "." + groupes[0]
        else:
            return None
    if not re.fullmatch(r"-?\d+(\.\d+)?", brut):
        return None
    valeur = float(brut)
    return -valeur if negatif else valeur


def _lignes(page, tolerance=2.5):
    """Les mots de la page, regroupés par ligne et ordonnés de gauche à droite."""
    lignes = {}
    for mot in page.extract_words():
        lignes.setdefault(round(mot["top"] / tolerance), []).append(mot)
    return [sorted(mots, key=lambda m: m["x0"])
            for _, mots in sorted(lignes.items())]


def _cellules(ligne):
    """Sépare une ligne en libellé et en montants situés.

    Deux groupes de chiffres appartiennent au même montant si l'espace qui
    les sépare tient dans une largeur et demie de caractère. Au-delà, c'est
    une autre colonne — voir l'en-tête du module pour la mesure.

    Le libellé s'arrête au premier montant, et c'est essentiel : ces PDF
    impriment deux tableaux côte à côte, si bien qu'une ligne porte le
    bilan à gauche et le compte de résultat à droite. Tout prendre donnerait
    « TOTAL ACTIF Achats de matières premières », qui ne ressemble plus à
    rien de reconnaissable.
    """
    libelle, montants = [], []
    for mot in ligne:
        texte = mot["text"]
        if not JETON.match(texte):
            if not montants:
                libelle.append(texte)
            continue
        largeur = (mot["x1"] - mot["x0"]) / max(1, len(texte))
        if montants and (mot["x0"] - montants[-1]["x1"]) < 1.5 * largeur:
            montants[-1]["texte"] += texte
            montants[-1]["x1"] = mot["x1"]
        else:
            montants.append({"texte": texte, "x0": mot["x0"], "x1": mot["x1"]})
    return " ".join(libelle), montants


def _colonne(montants, bord, marge=6.0):
    """Le montant aligné sur la colonne repérée par son bord droit.

    Les tableaux comptables alignent les nombres à droite : c'est `x1` qui
    identifie une colonne, et non `x0`, qui varie avec le nombre de
    chiffres. La marge écarte au passage la colonne « Note », qui porte de
    petits entiers sans rapport avec les montants.
    """
    for montant in montants:
        if abs(montant["x1"] - bord) <= marge:
            return _valeur(montant["texte"])
    return None


def _correspond(libelle, code, motifs, par_code):
    """Cette ligne porte-t-elle l'un des postes cherchés ?

    L'appariement est exact, sur le libellé entier. Une simple recherche
    accepterait « Remboursements des emprunts et autres dettes
    financières », qui se termine par le motif de la dette sans en être :
    la dette de Palm CI y perdait les 3 Md remboursés dans l'année.
    """
    if par_code:
        return code in motifs
    return any(re.fullmatch(motif, libelle.strip(), re.I) for motif in motifs)


def _unite(textes, page=None):
    """Le multiplicateur déclaré — unités, milliers, millions.

    L'unité se lit d'abord sur la page du bilan, et le document entier ne
    sert que de repli. Un même dépôt peut mêler les deux échelles : CIE
    publie ses comptes SYSCOHADA en milliers et son annexe IFRS en
    millions, et retenir l'annexe multipliait son bilan par mille.
    """
    if page is not None and 0 <= page < len(textes):
        for facteur, motif in UNITES:
            if motif.search(textes[page]):
                return facteur
    entier = "\n".join(textes)
    for facteur, motif in UNITES:
        if motif.search(entier):
            return facteur
    return 1


def _exercice(textes):
    """L'année d'arrêté la plus récente citée par le document.

    Un jeu d'états financiers cite deux exercices, celui qu'il présente et
    le précédent, dans un ordre qui varie. Nous retenons le plus récent —
    à défaut, la première date rencontrée désignerait le comparatif chez
    la moitié des émetteurs.
    """
    annees = {int(annee) for texte in textes
              for annee in DATE_BILAN.findall(texte)}
    return max(annees) if annees else None


def _releves(pages, postes, par_code):
    """Tous les relevés d'un côté du bilan, une entrée par page utile.

    Un relevé associe à chaque poste cherché la liste des montants trouvés
    sur sa ligne — la colonne n'est pas encore choisie, c'est l'identité
    comptable qui tranchera.
    """
    trouvailles = []
    for numero, lignes in enumerate(pages):
        page = {}
        for rang, ligne in enumerate(lignes):
            libelle, montants = _cellules(ligne)
            if not montants:
                continue
            mots = libelle.split()
            code = mots[0].upper() if mots else ""
            reste = " ".join(mots[1:]) if par_code else libelle
            for poste, motifs in postes.items():
                if _correspond(reste, code, motifs, par_code):
                    page.setdefault(poste, []).append(((numero, rang), montants))
        if "total_assets" in page or "total_passif" in page:
            trouvailles.append(page)
    return trouvailles


def _somme(releve, poste, bord, avant):
    """La somme des lignes d'un poste, dans la colonne retenue.

    `total_debt` agrège plusieurs lignes — emprunts, locations, crédits de
    trésorerie. Une ligne illisible parmi d'autres est ignorée, mais si
    aucune ne l'est le poste reste inconnu : zéro et « on ne sait pas » ne
    se confondent pas dans ce produit.

    Seules comptent les lignes situées **avant** le total, parce qu'un
    poste s'additionne toujours au-dessus de sa somme. C'est ce qui
    distingue la dette du bilan de « Emprunts & autres dettes
    financières » du tableau de flux, imprimé plus bas dans la même
    colonne et qui, sans cette règle, viendrait s'y ajouter.
    """
    lignes = releve.get(poste)
    if not lignes:
        return None
    valeurs = [valeur for ou, montants in lignes if ou < avant
               and (valeur := _colonne(montants, bord)) is not None]
    return sum(valeurs) if valeurs else None


def _accorder(actif, passif):
    """Trouve la colonne de l'exercice, par l'identité actif = passif.

    Renvoie (total, bord à l'actif, bord au passif, page de l'actif), ou
    None si aucune colonne de l'actif ne retrouve un total du passif —
    auquel cas nous refusons de lire le document plutôt que de choisir au
    hasard.

    Les deux montants doivent venir de deux cellules distinctes : une même
    cellule lue deux fois vérifierait évidemment l'égalité sans rien
    prouver. Les deux moitiés du bilan se présentent tantôt en vis-à-vis —
    même ligne, colonnes différentes — tantôt empilées — même colonne,
    lignes différentes. Il suffit que l'un des deux diffère.
    """
    for ou_actif, montants_actif in actif.get("total_assets") or []:
        for cellule in montants_actif:
            valeur = _valeur(cellule["texte"])
            if not valeur or valeur <= 0:
                continue
            for ou_passif, montants_passif in passif.get("total_passif") or []:
                meme_ligne = ou_actif == ou_passif
                for temoin in montants_passif:
                    if meme_ligne and abs(temoin["x1"] - cellule["x1"]) < 1:
                        continue
                    autre = _valeur(temoin["texte"])
                    if autre and abs(autre - valeur) <= TOLERANCE * valeur:
                        return valeur, (cellule["x1"], ou_actif), (temoin["x1"], ou_passif)
    return None


def lire(contenu, exercice=None):
    """Le bilan d'un PDF d'états financiers, ou None s'il n'y en a pas.

    `contenu` sont les octets du PDF. Renvoie les quatre grandeurs dont le
    moteur de screening a besoin, exprimées en francs CFA, accompagnées de
    leur provenance — le plan comptable reconnu et, s'il y a lieu, ce que
    ce plan ne permet pas de lire exactement.

    Renvoie None sans rien inventer lorsque le document ne porte pas de
    bilan : la BRVM publie sous le même intitulé des communiqués de
    résultats qui n'en contiennent aucun.
    """
    with pdfplumber.open(io.BytesIO(contenu)) as pdf:
        pages = [_lignes(page) for page in pdf.pages]
        textes = [page.extract_text() or "" for page in pdf.pages]

    # La BRVM annonce l'exercice dans l'intitulé du document ; c'est la
    # parole de l'émetteur, elle prime sur ce que nous croyons lire.
    annee = exercice or _exercice(textes)

    for plan, postes_actif, postes_passif, par_code in PLANS:
        for actif in _releves(pages, postes_actif, par_code):
            for passif in _releves(pages, postes_passif, par_code):
                accord = _accorder(actif, passif)
                if not accord:
                    continue
                total, (bord_actif, ou_actif), (bord_passif, ou_passif) = accord
                facteur = _unite(textes, ou_actif[0])
                if total * facteur < PLANCHER_BILAN:
                    continue
                postes = {
                    "cash_and_investments": _somme(
                        actif, "cash_and_investments", bord_actif, ou_actif),
                    "receivables": _somme(
                        actif, "receivables", bord_actif, ou_actif),
                    "total_debt": _somme(
                        passif, "total_debt", bord_passif, ou_passif),
                }
                # Un poste ne peut pas excéder le total dont il fait partie.
                # S'il le dépasse, c'est que la ligne lue n'est pas celle
                # que l'on croit, et le document est écarté : mieux vaut
                # « à vérifier » qu'un ratio calculé sur un poste étranger.
                if any(v is not None and v > total for v in postes.values()):
                    continue
                lu = {cle: _echelle(v, facteur) for cle, v in postes.items()}
                lu["total_assets"] = total * facteur
                lu["bilan_date"] = f"{annee}-12-31" if annee else None
                lu["bilan_plan"] = LIBELLES_PLANS[plan]
                lu["bilan_reserve"] = APPROXIMATIONS.get(plan)
                return lu
    return None


def _echelle(valeur, facteur):
    """Un montant ramené au franc, ou None s'il n'a pas été lu."""
    return None if valeur is None else valeur * facteur
