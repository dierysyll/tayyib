"""
Le fil de presse : des flux RSS francophones, choisis pour ce lecteur-ci.

Pourquoi ne pas se contenter de Yahoo
-------------------------------------
Yahoo Finance attache des dépêches à chaque valeur, ce qui est précieux :
c'est la seule source qui sache dire « ceci parle de LVMH ». Mais elle est
anglophone, généraliste américaine, et elle ne parlera jamais de la Bourse
de Casablanca ni d'un sukuk sénégalais.

Or le lecteur visé est francophone, souvent africain, et musulman. Ces trois
caractéristiques changent ce qui compte pour lui. On complète donc les
dépêches par valeur avec des fils thématiques en français, répartis en trois
rubriques :

  marches           l'actualité économique et boursière générale ;
  afrique           l'Afrique francophone et le Maghreb — la zone la moins
                    servie par les screeners existants, et celle dont les
                    places (BRVM, Casablanca) manquent justement à notre
                    univers. On ne peut pas les screener ; on peut au moins
                    en donner des nouvelles ;
  monde-musulman    ce qui concerne les musulmans au-delà de la finance.

Aucune clé d'API, aucune dépendance : ce sont des flux RSS publics, lus avec
la bibliothèque standard.

Ce que nous ne prétendons pas être
----------------------------------
Une rédaction. Nous agrégeons des titres publiés ailleurs, avec leur source
et un lien vers l'original. Nous ne réécrivons rien, nous ne résumons pas à
la main, et nous n'ajoutons aucun commentaire — en particulier aucun avis
religieux sur les sujets traités.
"""

import concurrent.futures as cf
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

RUBRIQUES = {
    "marches": {
        "id": "marches",
        "nom": "Marchés",
        "resume": "L'actualité économique et boursière.",
        "icone": "marche",
    },
    "afrique": {
        "id": "afrique",
        "nom": "Afrique francophone",
        "resume": "Le Maghreb et l'Afrique de l'Ouest — la zone la moins servie par les screeners.",
        "icone": "globe",
    },
    "monde-musulman": {
        "id": "monde-musulman",
        "nom": "Monde musulman",
        "resume": "Ce qui concerne les musulmans, au-delà de la finance.",
        "icone": "croissant",
    },
}

# Flux retenus après vérification : chacun répond, publie du français, et
# la colonne « images » dit s'il illustre ses articles. Ceux qui n'en ont
# pas restent utiles — un titre sans vignette vaut mieux qu'une rubrique
# vide — mais l'interface les présente autrement.
SOURCES = [
    # --- Marchés ---------------------------------------------------------
    {"nom": "Le Monde Économie", "rubrique": "marches",
     "url": "https://www.lemonde.fr/economie/rss_full.xml"},
    {"nom": "Franceinfo Économie", "rubrique": "marches",
     "url": "https://www.francetvinfo.fr/economie.rss"},
    {"nom": "La Tribune", "rubrique": "marches",
     "url": "https://www.latribune.fr/feed.xml"},

    # --- Afrique francophone --------------------------------------------
    {"nom": "Financial Afrik", "rubrique": "afrique",
     "url": "https://financialafrik.com/feed/"},
    {"nom": "RFI Afrique", "rubrique": "afrique",
     "url": "https://www.rfi.fr/fr/afrique/rss"},
    {"nom": "Hespress", "rubrique": "afrique",
     "url": "https://fr.hespress.com/feed"},
    {"nom": "Jeune Afrique", "rubrique": "afrique",
     "url": "https://www.jeuneafrique.com/feed/"},
    {"nom": "TSA Algérie", "rubrique": "afrique",
     "url": "https://www.tsa-algerie.com/feed/"},

    # --- Monde musulman --------------------------------------------------
    {"nom": "Saphirnews", "rubrique": "monde-musulman",
     "url": "https://www.saphirnews.com/xml/syndication.rss"},
    {"nom": "Middle East Eye", "rubrique": "monde-musulman",
     "url": "https://www.middleeasteye.net/fr/rss"},
    {"nom": "Anadolu", "rubrique": "monde-musulman",
     "url": "https://www.aa.com.tr/fr/rss/default?cat=guncel"},
]

NS = {
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "atom": "http://www.w3.org/2005/Atom",
}

# Certains serveurs renvoient 403 à un client sans en-tête de navigateur.
ENTETES = {
    "User-Agent": "Mozilla/5.0 (compatible; Tayyib/1.0; +https://tayyib.app)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

BALISES = re.compile(r"<[^>]+>")
ESPACES = re.compile(r"\s+")
IMG_SRC = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)

# Certains éditeurs ornent leurs titres d'emojis — « 💧 », « 📣 » — qui
# détonnent dans une interface qui n'en emploie aucun. On les retire de
# l'affichage : ce sont des ornements, ils ne portent pas de sens, et leur
# suppression ne dénature pas le titre. Le lien mène toujours à l'original.
EMOJIS = re.compile(
    "[\U0001F1E6-\U0001F1FF]{2}"          # drapeaux
    "|[\U0001F300-\U0001FAFF]"            # pictogrammes
    "|[☀-➿]"                    # symboles divers
    "|[️‍]"                     # sélecteurs de variante, liant
)


def sans_emoji(texte):
    if not texte:
        return texte
    return ESPACES.sub(" ", EMOJIS.sub("", texte)).strip()


def _texte_propre(brut, limite=240):
    """Un résumé lisible à partir d'un fragment HTML de flux RSS."""
    if not brut:
        return None
    texte = html.unescape(BALISES.sub(" ", brut))
    texte = ESPACES.sub(" ", texte).strip()
    if not texte:
        return None
    texte = sans_emoji(texte)
    if len(texte) > limite:
        coupe = texte[:limite].rsplit(" ", 1)[0]
        texte = coupe + "…"
    return texte or None


def _image(item):
    """L'illustration de l'article, selon les trois conventions en usage.

    Les flux ne s'accordent pas : les uns exposent `media:content`, les
    autres une `enclosure`, les derniers noient une balise `img` dans le
    corps HTML. On les lit toutes plutôt que d'en privilégier une.
    """
    for chemin in ("media:content", "media:thumbnail"):
        el = item.find(chemin, NS)
        if el is not None and el.get("url"):
            return el.get("url")

    enclosure = item.find("enclosure")
    if enclosure is not None and (enclosure.get("type") or "").startswith("image"):
        return enclosure.get("url")

    for champ, ns in (("content:encoded", NS), ("description", None)):
        el = item.find(champ, ns) if ns else item.find(champ)
        if el is not None and el.text:
            trouve = IMG_SRC.search(el.text)
            if trouve:
                return html.unescape(trouve.group(1))

    return None


def _date(item):
    """La date de publication, normalisée en ISO 8601 UTC."""
    for champ in ("pubDate", "{http://purl.org/dc/elements/1.1/}date"):
        brut = item.findtext(champ)
        if not brut:
            continue
        try:
            date = parsedate_to_datetime(brut)
        except (TypeError, ValueError):
            try:
                date = datetime.fromisoformat(brut.replace("Z", "+00:00"))
            except ValueError:
                continue
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.astimezone(timezone.utc).isoformat()
    return None


def _articles_du_flux(source, limite):
    try:
        requete = urllib.request.Request(source["url"], headers=ENTETES)
        with urllib.request.urlopen(requete, timeout=20) as reponse:
            brut = reponse.read()
        racine = ET.fromstring(brut)
    except Exception:
        # Un flux qui tombe ne doit pas vider la rubrique des autres.
        return []

    items = racine.findall(".//item") or racine.findall(".//atom:entry", NS)
    articles = []

    for item in items[:limite]:
        titre = (item.findtext("title") or item.findtext("atom:title", "", NS) or "").strip()
        lien = (item.findtext("link") or "").strip()
        if not lien:
            atom_lien = item.find("atom:link", NS)
            lien = atom_lien.get("href") if atom_lien is not None else ""
        if not titre or not lien:
            continue

        articles.append({
            "titre": sans_emoji(html.unescape(titre)),
            "lien": lien,
            "source": source["nom"],
            "rubrique": source["rubrique"],
            "publie": _date(item),
            "resume": _texte_propre(item.findtext("description")),
            "image": _image(item),
        })

    return articles


def collecte(par_source=12):
    """Tous les flux, en parallèle. Renvoie une liste d'articles triés du
    plus récent au plus ancien, dédoublonnés sur le lien."""
    with cf.ThreadPoolExecutor(max_workers=6) as executeur:
        lots = executeur.map(
            lambda s: _articles_du_flux(s, par_source), SOURCES
        )
        articles = [a for lot in lots for a in lot]

    uniques, vus = [], set()
    for article in sorted(articles, key=lambda a: a.get("publie") or "", reverse=True):
        if article["lien"] not in vus:
            vus.add(article["lien"])
            uniques.append(article)

    return uniques
