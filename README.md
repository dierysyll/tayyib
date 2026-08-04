# Tayyib

Screener boursier halal pour la place de Paris. Le nom vient de
*halalan tayyiban* : licite, et pur.

Les deux références du screening halal — Zoya et Musaffa — sont anglophones
et centrées sur les valeurs américaines. Un investisseur francophone qui
détient un PEA n'y trouve pas ses valeurs. Tayyib commence là où le manque
est réel : les 60 grandes valeurs d'Euronext Paris.

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
qu'un « conforme » faux.

**Une source datée plutôt qu'une source pratique.** Yahoo expose les mêmes
grandeurs à deux endroits, et les deux ne concordent pas : sa fiche de
synthèse annonce 4,05 Md€ de trésorerie pour L'Oréal, quand le bilan au
31/12/2025 en porte 9,90 Md€. Nous lisons le bilan publié, et lui seul, pour
tout ce qui entre dans les ratios — les trois montants viennent du même
arrêté comptable, et cet arrêté est affiché. Un ratio dont on ne peut pas
nommer la date n'est pas vérifiable.

## Les standards ne donnent pas le même résultat

Sur les 60 valeurs suivies :

| Standard | Conformes | À vérifier | Non conformes |
|---|---:|---:|---:|
| AAOIFI | 16 | 4 | 40 |
| Dow Jones | 17 | 4 | 39 |
| MSCI Islamic | 27 | 7 | 26 |

L'écart n'est pas une erreur. AAOIFI rapporte la dette à la **capitalisation
boursière**, MSCI au **total du bilan**. TotalEnergies est ainsi non conforme
selon AAOIFI (35,9 % de la capitalisation) et conforme selon MSCI (20,6 % du
bilan). C'est la même entreprise, le même jour.

Chaque fiche affiche les trois verdicts côte à côte, précisément pour que ce
point soit visible.

## Architecture

```
app.py                  routes Flask, filtres de rendu
refresh.py              collecte l'univers dans le cache
screening/
  standards.py          seuils et dénominateurs des trois standards
  sectors.py            filtre sectoriel (exclu / à vérifier / ok)
  engine.py             applique un standard à une société → verdict
data/
  universe.py           les 60 tickers suivis
  yahoo.py              collecte (bilan daté + capitalisation du jour)
  cache.py              cache disque JSON, écriture atomique
```

Ajouter une valeur : un ticker dans `data/universe.py`, puis `refresh.py`.
Ajouter un standard : une entrée dans `STANDARDS`. Rien d'autre à toucher.

## Lancer en local

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python refresh.py     # ~2 min, construit le cache
.venv/bin/python app.py         # http://localhost:5001
```

`refresh.py` conserve la version en cache d'un ticker qui échoue, plutôt que
de perdre une société sur un HTTP 429 passager.

## Limites connues

- Le **filtre des 5 %** n'est pas calculable (voir plus haut). C'est la
  principale limite, et elle est structurelle.
- Le **Dow Jones** rapporte les montants à la capitalisation *moyenne sur
  24 mois* ; nous utilisons celle du jour. Sur une valeur volatile, le
  verdict peut différer de l'indice officiel.
- La ligne « trésorerie et placements » exclut les **titres de
  participation** classés disponibles à la vente, qui ne portent pas
  intérêt. Conservateur pour certaines sociétés, discutable pour d'autres.
- La classification sectorielle de Yahoo est **grossière**.

## Avertissement

Tayyib est un outil d'information. Ce n'est **pas un conseil en
investissement** — les verdicts ne tiennent compte ni de votre situation, ni
de vos objectifs, et le conseil personnalisé est une activité réglementée.
Ce n'est **pas une fatwa** non plus : les standards implémentés sont des
conventions destinées à rendre le screening industrialisable, pas une
autorité religieuse.
