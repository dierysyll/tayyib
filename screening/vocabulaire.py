"""
Le vocabulaire sectoriel, traduit.

Yahoo Finance classe les sociétés dans une taxonomie anglophone : onze
secteurs, cent-trente industries. Les afficher tels quels à un lecteur
francophone lui demande de traduire lui-même « Consumer Defensive » ou
« Specialty Industrial Machinery » — c'est-à-dire de faire un effort que
l'outil devrait lui épargner, sur la seule colonne qui explique *pourquoi*
une valeur est écartée.

On traduit donc, sans toucher aux données : la classification d'origine
reste la clé de tri et la clé du filtre sectoriel (voir sectors.py, qui
cherche des motifs anglais). Seul l'affichage change, et le lecteur peut
revenir à l'anglais s'il préfère les intitulés de sa source.

Une traduction absente n'est pas une erreur : on rend l'original. Yahoo
ajoute des industries de temps en temps, et une étiquette anglaise vaut
mieux qu'un trou.
"""

LANGUES = {
    "fr": {"code": "fr", "nom": "Français", "code_pays": "FR"},
    "en": {"code": "en", "nom": "English", "code_pays": "EN"},
}

LANGUE_DEFAUT = "fr"


SECTEURS = {
    "Basic Materials": "Matériaux de base",
    "Communication Services": "Communication",
    "Consumer Cyclical": "Consommation discrétionnaire",
    "Consumer Defensive": "Consommation courante",
    "Energy": "Énergie",
    "Financial Services": "Services financiers",
    "Healthcare": "Santé",
    "Industrials": "Industrie",
    "Real Estate": "Immobilier",
    "Technology": "Technologie",
    "Utilities": "Services aux collectivités",
}


INDUSTRIES = {
    "Advertising Agencies": "Agences de publicité",
    "Aerospace & Defense": "Aéronautique et défense",
    "Agricultural Inputs": "Intrants agricoles",
    "Airlines": "Compagnies aériennes",
    "Airports & Air Services": "Aéroports et services aériens",
    "Aluminum": "Aluminium",
    "Apparel Manufacturing": "Fabrication de vêtements",
    "Apparel Retail": "Distribution de vêtements",
    "Asset Management": "Gestion d'actifs",
    "Auto & Truck Dealerships": "Concessions automobiles",
    "Auto Manufacturers": "Constructeurs automobiles",
    "Auto Parts": "Équipementiers automobiles",
    "Banks - Diversified": "Banques diversifiées",
    "Banks - Regional": "Banques régionales",
    "Beverages - Brewers": "Brasseries",
    "Beverages - Non-Alcoholic": "Boissons sans alcool",
    "Beverages - Wineries & Distilleries": "Vins et spiritueux",
    "Biotechnology": "Biotechnologies",
    "Broadcasting": "Audiovisuel",
    "Building Materials": "Matériaux de construction",
    "Building Products & Equipment": "Produits et équipements du bâtiment",
    "Capital Markets": "Marchés de capitaux",
    "Chemicals": "Chimie",
    "Communication Equipment": "Équipements de télécommunication",
    "Computer Hardware": "Matériel informatique",
    "Confectioners": "Confiserie",
    "Conglomerates": "Conglomérats",
    "Consulting Services": "Conseil",
    "Consumer Electronics": "Électronique grand public",
    "Copper": "Cuivre",
    "Credit Services": "Crédit à la consommation",
    "Department Stores": "Grands magasins",
    "Diagnostics & Research": "Diagnostic et recherche",
    "Discount Stores": "Magasins à prix réduits",
    "Drug Manufacturers - General": "Laboratoires pharmaceutiques",
    "Drug Manufacturers - Specialty & Generic": "Pharmacie de spécialité et générique",
    "Education & Training Services": "Éducation et formation",
    "Electrical Equipment & Parts": "Équipements électriques",
    "Electronic Components": "Composants électroniques",
    "Electronic Gaming & Multimedia": "Jeu vidéo et multimédia",
    "Electronics & Computer Distribution": "Distribution électronique et informatique",
    "Engineering & Construction": "Ingénierie et construction",
    "Entertainment": "Divertissement",
    "Farm & Heavy Construction Machinery": "Machines agricoles et de chantier",
    "Farm Products": "Produits agricoles",
    "Financial Conglomerates": "Conglomérats financiers",
    "Financial Data & Stock Exchanges": "Données financières et places boursières",
    "Food Distribution": "Distribution alimentaire",
    "Footwear & Accessories": "Chaussures et accessoires",
    "Furnishings, Fixtures & Appliances": "Ameublement et électroménager",
    "Gambling": "Jeux d'argent",
    "Gold": "Or",
    "Grocery Stores": "Supermarchés",
    "Healthcare Plans": "Assurance santé",
    "Home Improvement Retail": "Bricolage et équipement de la maison",
    "Household & Personal Products": "Produits d'hygiène et d'entretien",
    "Industrial Distribution": "Distribution industrielle",
    "Information Technology Services": "Services informatiques",
    "Infrastructure Operations": "Exploitation d'infrastructures",
    "Insurance - Diversified": "Assurance diversifiée",
    "Insurance - Life": "Assurance vie",
    "Insurance - Property & Casualty": "Assurance dommages",
    "Insurance - Reinsurance": "Réassurance",
    "Insurance - Specialty": "Assurance spécialisée",
    "Insurance Brokers": "Courtage en assurance",
    "Integrated Freight & Logistics": "Fret et logistique",
    "Internet Content & Information": "Contenus et services en ligne",
    "Internet Retail": "Commerce en ligne",
    "Lodging": "Hôtellerie",
    "Lumber & Wood Production": "Bois et sciages",
    "Luxury Goods": "Produits de luxe",
    "Marine Shipping": "Transport maritime",
    "Medical Care Facilities": "Établissements de soins",
    "Medical Devices": "Dispositifs médicaux",
    "Medical Distribution": "Distribution médicale",
    "Medical Instruments & Supplies": "Instruments et consommables médicaux",
    "Metal Fabrication": "Transformation des métaux",
    "Oil & Gas E&P": "Exploration et production pétrolière",
    "Oil & Gas Equipment & Services": "Services pétroliers",
    "Oil & Gas Integrated": "Pétrole et gaz intégrés",
    "Oil & Gas Midstream": "Transport et stockage d'hydrocarbures",
    "Oil & Gas Refining & Marketing": "Raffinage et distribution",
    "Other Industrial Metals & Mining": "Autres métaux industriels et mines",
    "Other Precious Metals & Mining": "Autres métaux précieux et mines",
    "Packaged Foods": "Produits alimentaires transformés",
    "Packaging & Containers": "Emballage",
    "Paper & Paper Products": "Papier et produits papetiers",
    "Pharmaceutical Retailers": "Pharmacies",
    "Publishing": "Édition",
    "REIT - Diversified": "Foncière diversifiée",
    "REIT - Industrial": "Foncière industrielle",
    "REIT - Office": "Foncière de bureaux",
    "REIT - Residential": "Foncière résidentielle",
    "REIT - Retail": "Foncière commerciale",
    "Railroads": "Chemins de fer",
    "Real Estate - Development": "Promotion immobilière",
    "Real Estate - Diversified": "Immobilier diversifié",
    "Real Estate Services": "Services immobiliers",
    "Recreational Vehicles": "Véhicules de loisirs",
    "Rental & Leasing Services": "Location et crédit-bail",
    "Residential Construction": "Construction résidentielle",
    "Resorts & Casinos": "Complexes hôteliers et casinos",
    "Restaurants": "Restauration",
    "Scientific & Technical Instruments": "Instruments scientifiques et techniques",
    "Security & Protection Services": "Sécurité et protection",
    "Semiconductor Equipment & Materials": "Équipements pour semi-conducteurs",
    "Semiconductors": "Semi-conducteurs",
    "Software - Application": "Logiciels applicatifs",
    "Software - Infrastructure": "Logiciels d'infrastructure",
    "Specialty Business Services": "Services aux entreprises",
    "Specialty Chemicals": "Chimie de spécialité",
    "Specialty Industrial Machinery": "Machines industrielles spécialisées",
    "Specialty Retail": "Distribution spécialisée",
    "Staffing & Employment Services": "Travail temporaire et recrutement",
    "Steel": "Acier",
    "Telecom Services": "Télécommunications",
    "Textile Manufacturing": "Industrie textile",
    "Thermal Coal": "Charbon thermique",
    "Tobacco": "Tabac",
    "Tools & Accessories": "Outillage",
    "Travel Services": "Voyage et tourisme",
    "Trucking": "Transport routier",
    "Uranium": "Uranium",
    "Utilities - Diversified": "Services collectifs diversifiés",
    "Utilities - Independent Power Producers": "Producteurs d'électricité indépendants",
    "Utilities - Regulated Electric": "Électricité régulée",
    "Utilities - Regulated Gas": "Gaz régulé",
    "Utilities - Regulated Water": "Eau régulée",
    "Utilities - Renewable": "Énergies renouvelables",
    "Waste Management": "Gestion des déchets",
}


def normalise(langue):
    """La langue demandée, ou le français si elle n'est pas gérée."""
    return langue if langue in LANGUES else LANGUE_DEFAUT


def secteur(nom, langue=LANGUE_DEFAUT):
    """Le libellé d'un secteur dans la langue demandée."""
    if not nom:
        return None
    if normalise(langue) == "fr":
        return SECTEURS.get(nom, nom)
    return nom


def industrie(nom, langue=LANGUE_DEFAUT):
    """Le libellé d'une industrie dans la langue demandée."""
    if not nom:
        return None
    if normalise(langue) == "fr":
        return INDUSTRIES.get(nom, nom)
    return nom


def activite(societe, langue=LANGUE_DEFAUT):
    """L'intitulé d'activité le plus précis disponible : l'industrie si
    Yahoo la renseigne, le secteur sinon."""
    return (
        industrie(societe.get("industry"), langue)
        or secteur(societe.get("sector"), langue)
    )
