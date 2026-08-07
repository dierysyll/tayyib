# Tayyib

Screener boursier halal, en français, sur les places du monde entier. Le nom
vient de *halalan tayyiban* : licite, et pur.

Les deux références du screening halal — Zoya et Musaffa — sont anglophones et
centrées sur les valeurs américaines. Un investisseur francophone qui détient
un PEA n'y trouve pas ses valeurs, et un musulman qui veut regarder Riyad,
Istanbul ou Kuala Lumpur n'y trouve pas davantage son compte. Tayyib est né du
premier manque — Euronext Paris — et couvre aujourd'hui **29 places** sur
quatre continents. Paris reste la place de référence.

Parmi elles, la **BRVM d'Abidjan**, place commune aux huit pays de l'UEMOA :
absente de Yahoo Finance, elle est collectée directement à sa source — les
cours sur la page de cotation, les comptes dans les états financiers que
chaque société y dépose. C'est la seule place où un épargnant sénégalais ou
ivoirien achète dans sa propre monnaie, et aucun autre screener halal ne la
couvre.

## Ce que fait l'application

Pour chaque société, deux filtres appliqués dans cet ordre :

1. **Le filtre sectoriel.** Banque, assurance et crédit conventionnels,
   alcool, tabac, jeux d'argent, contenu pour adultes sont écartés sans
   examen des comptes. D'autres secteurs — armement, grande distribution,
   hôtellerie, foncières — sont classés **à vérifier**, parce que
   l'intitulé sectoriel ne suffit pas à trancher.

2. **Les ratios financiers**, selon le standard choisi par l'utilisateur :
   AAOIFI, Dow Jones Islamic Market ou MSCI Islamic.

Le résultat est un verdict à trois états : conforme, non conforme,
à vérifier.

Autour du screener, quatre rubriques :

- **Analyses** — les basculements de conformité au dernier arrêté comptable
  (une valeur qui se désendette redevient conforme, et personne ne le publie),
  les palmarès des conformes, le taux de conformité par place, et les valeurs
  sur lesquelles les trois standards se contredisent.
- **Purification** — le montant à purifier sur les dividendes perçus.
- **Zakat** — l'assiette selon l'intention de détention, le nissab calculé sur
  le cours du jour de l'or et de l'argent, le taux de 2,5 %.
- **Actualités** — un fil agrégé, avec le verdict attaché à chaque société
  citée. C'est la rubrique la plus faible des quatre, et la page le dit.

## Le parti pris : ne jamais transformer une incertitude en verdict

C'est ce qui distingue Tayyib de ses concurrents, et c'est un choix de
conception, pas une limite subie.

**Le filtre des 5 %.** Les trois standards imposent que les revenus tirés
d'activités non conformes restent sous 5 % du chiffre d'affaires. Ce chiffre
ne se déduit pas des données de marché : il se lit dans le rapport annuel, et
aucune source gratuite ne le publie. Nous ne l'estimons pas et nous ne le
passons pas sous silence — tout verdict « conforme » est accompagné de la
mention correspondante.

**Le troisième verdict.** « Aerospace & Defense » range sous une même
étiquette l'aviation civile et l'armement ; la grande distribution vend de
l'alcool sans que ce soit son métier. Un « à vérifier » honnête vaut mieux
qu'un « conforme » faux. Au Caire et à Karachi, Yahoo ne renseigne pas le
secteur d'activité : ces valeurs tombent donc en « à vérifier », et la place
le signale.

**Une source datée plutôt qu'une source pratique.** Yahoo expose les mêmes
grandeurs à deux endroits, et les deux ne concordent pas : sa fiche de
synthèse annonce 4,05 Md€ de trésorerie pour L'Oréal, quand le bilan au
31/12/2025 en porte 9,90 Md€. Nous lisons le bilan publié, et lui seul, pour
tout ce qui entre dans les ratios — les trois montants viennent du même
arrêté comptable, et cet arrêté est affiché.

**Une colonne choisie, pas devinée.** Les bilans de la BRVM arrivent en PDF,
et l'actif SYSCOHADA s'y présente en trois colonnes : brut, amortissements,
net. Chez Erium, 25,4 Md, 10,8 Md et 14,6 Md sur la même ligne — se tromper
de colonne surestimerait l'actif de 74 %, donc sous-estimerait tous les
ratios, donc déclarerait conformes des sociétés qui ne le sont pas.
`data/bilans.py` ne devine pas : il retient la colonne qui **égale le total
du passif**, et refuse le document quand aucune n'y parvient. La même
vérification attrape une page mal appariée, une unité mal lue ou un nombre
mal découpé.

**Bloqué n'est pas absent.** Yahoo limite le débit. Un symbole qu'on n'a pas
pu lire et un symbole qui n'existe pas produisent le même silence, mais
appellent des réponses opposées : le second se corrige, le premier se
redemande. `data/yahoo.py` lève `SourceIndisponible` dans le second cas, et
`refresh.py` réessaie après une longue pause. Sans cette distinction, une
collecte trop rapide fait disparaître des places entières du produit.

## Les standards ne donnent pas le même résultat

L'écart n'est pas une erreur. AAOIFI rapporte la dette à la **capitalisation
boursière**, MSCI au **total du bilan**. Une valeur très bien valorisée —
Broadcom, Eli Lilly — passe donc largement chez AAOIFI et échoue chez MSCI,
puisque sa capitalisation est plusieurs fois son bilan. C'est la même
entreprise, le même jour.

Chaque fiche affiche les trois verdicts côte à côte, et la page Analyses
recense les désaccords tranchés, précisément pour que ce point soit visible.

## Les devises

Les capitalisations et les valorisations de portefeuille sont converties en
euros (`data/fx.py`), sans quoi trier l'univers par taille placerait Jakarta
au-dessus d'Apple — une capitalisation en roupies indonésiennes se compte en
centaines de milliers de milliards. Le montant en devise de cotation reste
affiché sur chaque fiche.

Les **ratios de screening ne sont jamais convertis** : dette et capitalisation
d'une même société sont dans la même devise, le rapport est invariant. Un taux
de change erroné fausse l'ordre d'affichage, jamais un verdict.

Attention à Londres, cotée en **pence** et non en livres : l'oubli est
silencieux et fausse la taille des valeurs britanniques d'un facteur cent.

## Architecture

```
app.py                  routes Flask, filtres de rendu
refresh.py              collecte l'univers dans le cache
charts.py               projection SVG de la courbe de cours
screening/
  standards.py          seuils et dénominateurs des six standards
  sectors.py            filtre sectoriel (exclu / à vérifier / ok)
  engine.py             applique un standard à une société → verdict
  analyses.py           lectures à l'échelle de l'univers entier
  vocabulaire.py        secteurs et industries traduits (FR/EN)
  alias.py              noms usuels et recherche sans accents
data/
  universe.py           les places de marché et leurs valeurs
  yahoo.py              collecte (bilan daté + capitalisation + actualités)
  brvm.py               collecte directe de la cote d'Abidjan
  bilans.py             lecture des bilans SYSCOHADA et IFRS en PDF
  presse.py             flux RSS francophones, en trois rubriques
  fx.py                 taux de change, cours de l'or et de l'argent
  cache.py              cache disque en deux étages
```

**La recherche.** Yahoo connaît « Saudi Arabian Oil Company » ; personne ne
cherche autre chose qu'« Aramco ». `screening/alias.py` porte les noms usuels
— marque commerciale, ancien nom, sigle en usage, translittération — et
dépouille les clés de leurs accents, des deux côtés : « hermes » trouve
Hermès, « socgen » trouve la Société Générale. Rien qui devine : « pétrole »
ne renvoie pas à TotalEnergies, parce qu'un moteur qui extrapole finit par se
tromper.

Le cache est scindé : `cache/index.json` porte l'essentiel de chaque valeur et
sert toutes les pages de liste ; `cache/valeurs/<symbole>.json` porte le détail
— six ans de cours hebdomadaires, comptes annuels, dividendes — et n'est lu
qu'à l'ouverture d'une fiche. Avec plus de mille valeurs, un fichier unique
pèserait une vingtaine de mégaoctets qu'il faudrait charger pour afficher un
tableau qui n'en utilise rien.

Ajouter une valeur : un symbole dans la place correspondante de
`data/universe.py`, puis `refresh.py`. Ajouter un standard : une entrée dans
`STANDARDS`. Ajouter une place : une entrée dans `PLACES`, avec sa devise.

## Lancer en local

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python refresh.py     # collecte complète, ~1 h
.venv/bin/python app.py         # http://localhost:5001
```

`refresh.py` reprend où il s'est arrêté : un symbole déjà collecté depuis moins
de vingt heures n'est pas redemandé, et l'index est réécrit tous les quarante
titres, de sorte que le site sert un univers qui grandit pendant la collecte.

```bash
.venv/bin/python refresh.py --brvm                 # seulement la cote d'Abidjan
.venv/bin/python refresh.py --brvm-bilans          # + relire les états financiers
.venv/bin/python refresh.py --places paris,riyad   # une ou plusieurs places
.venv/bin/python refresh.py --force                # tout redemander
.venv/bin/python refresh.py --actus                # seulement le fil d'actualité
.venv/bin/python refresh.py --index                # réécrire l'index depuis le disque
```

## Limites connues

- Le **filtre des 5 %** n'est pas calculable (voir plus haut). C'est la
  principale limite, et elle est structurelle.
- Sur la **BRVM**, la **capitalisation boursière** est inconnue : la source
  ne publie aucun nombre d'actions à jour, celui de ses fiches émetteurs
  datant de 2015. Les trois standards qui divisent par elle — AAOIFI, Dow
  Jones, S&P Shariah — ne peuvent donc pas conclure sur cette place, là où
  MSCI Islamic, FTSE Shariah et SC Malaisie tranchent normalement.
- Les **bilans de la BRVM** sont lus dans les PDF déposés par les émetteurs,
  et 23 des 28 sociétés que le secteur ne tranche pas d'emblée sont
  couvertes. Les cinq autres publient sous une forme que `data/bilans.py`
  refuse de lire plutôt que d'interpréter de travers ; elles restent
  « à vérifier ».
- **Casablanca** n'est toujours pas couverte, et la source le dit mal : elle
  répond « Too Many Requests » là où elle devrait répondre « symbole
  inconnu », ce qui donne l'illusion d'une place récupérable en réessayant.
  Tunis, Lagos, Mascate et Manama sont dans le même cas.
- Le **Dow Jones** rapporte les montants à la capitalisation *moyenne sur
  24 mois* ; nous utilisons celle du jour. Sur une valeur volatile, le
  verdict peut différer de l'indice officiel.
- La ligne « trésorerie et placements » exclut les **titres de
  participation** classés disponibles à la vente, qui ne portent pas
  intérêt. Conservateur pour certaines sociétés, discutable pour d'autres.
- La classification sectorielle de Yahoo est **grossière**, et **absente**
  au Caire et à Karachi.
- L'assiette zakatable de long terme est **approchée** par la part de
  trésorerie et de créances au bilan. L'AAOIFI recommande d'y ajouter les
  stocks, que Yahoo ne publie pas. L'approximation est signalée sur chaque
  ligne du calculateur.

## Avertissement

Tayyib est un outil d'information. Ce n'est **pas un conseil en
investissement** — les verdicts ne tiennent compte ni de votre situation, ni
de vos objectifs, et le conseil personnalisé est une activité réglementée.
Ce n'est **pas une fatwa** non plus : les standards implémentés sont des
conventions destinées à rendre le screening industrialisable, pas une
autorité religieuse.
