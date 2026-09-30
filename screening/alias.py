"""
Les noms usuels, et l'insensibilité aux accents.

Deux raisons distinctes font échouer une recherche parfaitement légitime.

**Le nom légal n'est pas le nom usuel.** Yahoo connaît « Saudi Arabian Oil
Company » ; personne ne cherche autre chose qu'« Aramco ». De même pour
Alphabet contre Google, Meta contre Facebook, Inditex contre Zara, Türk
Hava Yollari contre Turkish Airlines. Un moteur qui ne trouve pas Aramco
quand on tape Aramco n'est pas un moteur.

**Les accents.** « Hermès », « L'Oréal », « Société Générale », « Nestlé »,
« Telefónica » : le lecteur tape rarement les accents dans un champ de
recherche, et il n'a pas à le faire. On compare donc des chaînes
dépouillées de leurs diacritiques, des deux côtés.

Ce fichier ne contient que des alias que l'on peut justifier : marque
commerciale, ancien nom, sigle en usage, translittération. Pas de mots-clés
d'ambiance — « pétrole » ne renvoie pas à TotalEnergies, parce qu'un moteur
qui devine finit par se tromper.

Attention aux sigles ambigus : `BA` est Boeing à New York et BAE Systems à
Londres. Comme les alias sont attachés à un symbole précis et jamais
partagés, les deux cohabitent sans se confondre.
"""

import unicodedata


def sans_accents(texte):
    """La chaîne dépouillée de ses diacritiques, en minuscules.

    C'est la forme sur laquelle on compare : elle doit être appliquée
    identiquement à l'index et à la saisie, sans quoi elle ne sert à rien.
    """
    if not texte:
        return ""
    decompose = unicodedata.normalize("NFD", texte)
    return "".join(c for c in decompose if not unicodedata.combining(c)).lower()


# Symbole → autres noms sous lesquels la société est réellement cherchée.
ALIAS = {
    # --- Paris ------------------------------------------------------------
    "TTE.PA": ["total", "total energies", "elf"],
    "OR.PA": ["loreal"],
    "RMS.PA": ["hermes"],
    "GLE.PA": ["societe generale", "socgen", "sg"],
    "BNP.PA": ["bnp", "paribas"],
    "ACA.PA": ["credit agricole", "casa"],
    "STLAP.PA": ["peugeot", "citroen", "fiat", "chrysler", "opel", "psa", "jeep"],
    "ORA.PA": ["france telecom"],
    "ENGI.PA": ["gdf", "gdf suez", "suez"],
    "EL.PA": ["essilor", "luxottica", "ray ban", "rayban"],
    "KER.PA": ["gucci", "saint laurent", "balenciaga", "ppr", "bottega"],
    "MC.PA": ["vuitton", "louis vuitton", "moet", "hennessy", "dior", "sephora"],
    "CS.PA": ["axa"],
    "SU.PA": ["schneider"],
    "MT.AS": ["arcelor", "mittal"],
    "STMPA.PA": ["stmicro", "st micro", "stm"],
    "AI.PA": ["air liquide"],
    "DG.PA": ["vinci"],
    "SGO.PA": ["saint gobain"],
    "RI.PA": ["ricard", "pernod"],
    "BN.PA": ["danone", "evian"],
    "CA.PA": ["carrefour"],
    "ATO.PA": ["atos"],
    "PUB.PA": ["publicis"],
    "VIE.PA": ["veolia"],
    "ADP.PA": ["aeroports de paris", "roissy", "orly"],
    "AF.PA": ["air france", "klm"],
    "URW.PA": ["unibail", "westfield"],

    # --- Europe -----------------------------------------------------------
    "ASML.AS": ["asml"],
    "PRX.AS": ["prosus"],
    "INGA.AS": ["ing"],
    "HEIA.AS": ["heineken"],
    "ABI.BR": ["ab inbev", "inbev", "budweiser", "stella artois", "leffe", "jupiler"],
    "NESN.SW": ["nestle", "nespresso"],
    "NOVN.SW": ["novartis"],
    "UBSG.SW": ["ubs", "credit suisse"],
    "CFR.SW": ["richemont", "cartier", "van cleef"],
    "ZURN.SW": ["zurich"],
    "SAP.DE": ["sap"],
    "SIE.DE": ["siemens"],
    "VOW3.DE": ["volkswagen", "vw", "audi", "skoda", "seat"],
    "MBG.DE": ["mercedes", "daimler"],
    "BMW.DE": ["bmw", "mini"],
    "ALV.DE": ["allianz"],
    "DTE.DE": ["deutsche telekom", "telekom", "t mobile"],
    "BAS.DE": ["basf"],
    "BAYN.DE": ["bayer"],
    "ADS.DE": ["adidas"],
    "PUM.DE": ["puma"],
    "DHL.DE": ["dhl", "deutsche post"],
    "SHEL.L": ["shell"],
    "AZN.L": ["astrazeneca", "astra zeneca"],
    "HSBA.L": ["hsbc"],
    "ULVR.L": ["unilever", "dove", "knorr"],
    "BP.L": ["bp", "british petroleum"],
    "RIO.L": ["rio tinto"],
    "GSK.L": ["gsk", "glaxo", "glaxosmithkline"],
    "DGE.L": ["diageo", "guinness", "johnnie walker"],
    "BATS.L": ["bat", "british american tobacco", "lucky strike"],
    "VOD.L": ["vodafone"],
    "BA.L": ["bae", "bae systems"],
    "TSCO.L": ["tesco"],
    "ENI.MI": ["eni", "agip"],
    "ENEL.MI": ["enel"],
    "RACE.MI": ["ferrari"],
    "ISP.MI": ["intesa"],
    "UCG.MI": ["unicredit"],
    "STLAM.MI": ["stellantis"],
    "MONC.MI": ["moncler"],
    "ITX.MC": ["inditex", "zara", "bershka", "massimo dutti"],
    "SAN.MC": ["santander"],
    "BBVA.MC": ["bbva"],
    "TEF.MC": ["telefonica", "movistar", "o2"],
    "IBE.MC": ["iberdrola"],
    "IAG.MC": ["iberia", "british airways", "vueling"],
    "GALP.LS": ["galp"],
    "NOVO-B.CO": ["novo nordisk", "novo", "ozempic", "wegovy"],
    "MAERSK-B.CO": ["maersk"],
    "CARL-B.CO": ["carlsberg", "kronenbourg", "tuborg"],
    "PNDORA.CO": ["pandora"],
    "EQNR.OL": ["equinor", "statoil"],
    "MOWI.OL": ["mowi", "marine harvest"],
    "VOLV-B.ST": ["volvo"],
    "ERIC-B.ST": ["ericsson"],
    "HM-B.ST": ["h m", "hennes", "hm"],
    "ATCO-A.ST": ["atlas copco"],
    "SAAB-B.ST": ["saab"],
    "ELUX-B.ST": ["electrolux"],
    "PKN.WA": ["orlen", "pkn"],
    "RYA.IR": ["ryanair"],

    # --- Amériques --------------------------------------------------------
    "GOOGL": ["google", "youtube", "android", "gmail"],
    "META": ["facebook", "instagram", "whatsapp"],
    "BRK-B": ["berkshire", "buffett", "warren buffett"],
    "XOM": ["exxon", "exxonmobil", "esso", "mobil"],
    "JPM": ["jp morgan", "jpmorgan", "chase"],
    "PG": ["procter", "procter gamble", "p g", "pampers", "gillette"],
    "JNJ": ["johnson", "johnson johnson", "j j"],
    "KO": ["coca", "coca cola", "coke", "fanta", "sprite"],
    "PEP": ["pepsi", "pepsico", "lays", "doritos"],
    "MCD": ["mcdonald", "mcdonalds", "mcdo"],
    "DIS": ["disney", "walt disney", "pixar", "marvel"],
    "PM": ["philip morris", "marlboro", "iqos"],
    "MO": ["altria"],
    "LLY": ["lilly", "eli lilly", "mounjaro", "zepbound"],
    "UNH": ["unitedhealth", "united health"],
    "CRM": ["salesforce"],
    "AVGO": ["broadcom", "vmware"],
    "ACN": ["accenture"],
    "TXN": ["texas instruments"],
    "MU": ["micron"],
    "AMD": ["amd", "advanced micro"],
    "INTC": ["intel"],
    "IBM": ["ibm", "international business machines"],
    "ORCL": ["oracle"],
    "ADBE": ["adobe", "photoshop"],
    "NFLX": ["netflix"],
    "SBUX": ["starbucks"],
    "NKE": ["nike"],
    "WMT": ["walmart"],
    "HD": ["home depot"],
    "LOW": ["lowes"],
    "CVX": ["chevron", "texaco"],
    "BA": ["boeing"],
    "LMT": ["lockheed", "lockheed martin"],
    "RTX": ["raytheon"],
    "NOC": ["northrop", "northrop grumman"],
    "GD": ["general dynamics"],
    "CAT": ["caterpillar"],
    "DE": ["john deere", "deere"],
    "GE": ["general electric"],
    "F": ["ford"],
    "GM": ["general motors", "chevrolet", "cadillac"],
    "UPS": ["ups", "united parcel"],
    "FDX": ["fedex"],
    "PYPL": ["paypal"],
    "UBER": ["uber"],
    "ABNB": ["airbnb"],
    "COIN": ["coinbase"],
    "PLTR": ["palantir"],
    "SMCI": ["supermicro", "super micro"],
    "QCOM": ["qualcomm", "snapdragon"],
    "CSCO": ["cisco"],
    "PFE": ["pfizer"],
    "MRK": ["merck"],
    "ABBV": ["abbvie", "humira"],
    "AMGN": ["amgen"],
    "TMO": ["thermo fisher"],
    "COST": ["costco"],
    "TJX": ["tj maxx", "tk maxx"],
    "MDLZ": ["mondelez", "oreo", "milka", "lu"],
    "MAR": ["marriott"],
    "HLT": ["hilton"],
    "BKNG": ["booking", "booking com", "kayak"],
    "RY.TO": ["rbc", "royal bank"],
    "TD.TO": ["td bank", "toronto dominion"],
    "BNS.TO": ["scotiabank", "scotia"],
    "BMO.TO": ["bmo", "bank of montreal"],
    "ENB.TO": ["enbridge"],
    "SHOP.TO": ["shopify"],
    "ATD.TO": ["couche tard", "circle k"],
    "QSR.TO": ["burger king", "tim hortons", "restaurant brands"],

    # --- Golfe ------------------------------------------------------------
    "2222.SR": ["aramco", "saudi aramco"],
    "1120.SR": ["al rajhi", "alrajhi", "rajhi"],
    "2010.SR": ["sabic"],
    "7010.SR": ["stc", "saudi telecom"],
    "1180.SR": ["snb", "saudi national bank", "al ahli", "ncb"],
    "1211.SR": ["maaden", "ma aden"],
    "2280.SR": ["almarai"],
    "4190.SR": ["jarir"],
    "1150.SR": ["alinma"],
    "7020.SR": ["mobily", "etihad etisalat"],
    "4013.SR": ["dr sulaiman al habib", "habib"],
    "QNBK.QA": ["qnb", "qatar national bank"],
    "ORDS.QA": ["ooredoo", "qtel"],
    "IQCD.QA": ["industries qatar"],
    "QGTS.QA": ["nakilat"],
    "QIBK.QA": ["qib", "qatar islamic bank"],
    "MARK.QA": ["masraf al rayan", "al rayan"],
    "NBK.KW": ["nbk", "national bank of kuwait"],
    "KFH.KW": ["kfh", "kuwait finance house"],
    "ZAIN.KW": ["zain"],
    "EMAAR.AE": ["emaar", "burj khalifa", "dubai mall"],
    "EMIRATESNBD.AE": ["emirates nbd", "enbd"],
    "DIB.AE": ["dubai islamic bank", "dib"],
    "SALIK.AE": ["salik"],
    "DEWA.AE": ["dewa"],

    # --- Turquie ----------------------------------------------------------
    "THYAO.IS": ["turkish airlines", "turk hava yollari", "thy"],
    "ASELS.IS": ["aselsan"],
    "BIMAS.IS": ["bim"],
    "TUPRS.IS": ["tupras"],
    "FROTO.IS": ["ford otosan", "ford"],
    "TOASO.IS": ["tofas"],
    "TCELL.IS": ["turkcell"],
    "KCHOL.IS": ["koc", "koc holding"],
    "SAHOL.IS": ["sabanci"],
    "EREGL.IS": ["erdemir", "eregli"],
    "PGSUS.IS": ["pegasus"],
    "ARCLK.IS": ["arcelik", "beko"],
    "MGROS.IS": ["migros"],
    "ULKER.IS": ["ulker"],
    "CCOLA.IS": ["coca cola icecek"],
    "AEFES.IS": ["efes", "anadolu efes"],

    # --- Asie du Sud-Est --------------------------------------------------
    "1155.KL": ["maybank", "malayan banking"],
    "1023.KL": ["cimb"],
    "1295.KL": ["public bank"],
    "5347.KL": ["tenaga"],
    "4863.KL": ["telekom malaysia", "tm"],
    "6012.KL": ["maxis"],
    "3182.KL": ["genting"],
    "5183.KL": ["petronas chemicals", "petronas"],
    "6033.KL": ["petronas gas"],
    "5681.KL": ["petronas dagangan"],
    "3816.KL": ["misc"],
    "5225.KL": ["ihh", "ihh healthcare"],
    "6888.KL": ["axiata", "celcom"],
    "5296.KL": ["mr diy"],
    "BBCA.JK": ["bca", "bank central asia"],
    "BBRI.JK": ["bri", "bank rakyat"],
    "BMRI.JK": ["mandiri", "bank mandiri"],
    "BBNI.JK": ["bni", "bank negara"],
    "TLKM.JK": ["telkom", "telkomsel"],
    "ASII.JK": ["astra"],
    "UNVR.JK": ["unilever indonesia"],
    "GOTO.JK": ["goto", "gojek", "tokopedia"],
    "ICBP.JK": ["indofood cbp", "indomie"],
    "INDF.JK": ["indofood"],

    # --- Afrique du Nord et Moyen-Orient ----------------------------------
    "COMI.CA": ["cib", "commercial international bank"],
    "ETEL.CA": ["telecom egypt", "we"],
    "ORAS.CA": ["orascom"],
    "SWDY.CA": ["elsewedy", "el sewedy"],
    "TMGH.CA": ["talaat moustafa"],
    "HRHO.CA": ["efg hermes", "efg"],

    # --- Asie du Sud ------------------------------------------------------
    "OGDC.KA": ["ogdcl", "oil and gas development"],
    "LUCK.KA": ["lucky cement"],
    "HBL.KA": ["habib bank"],
    "MEBL.KA": ["meezan", "meezan bank"],
    "PSO.KA": ["pakistan state oil"],
    "ENGRO.KA": ["engro"],
    "UBL.KA": ["united bank"],
    "RELIANCE.NS": ["reliance", "jio", "ril"],
    "TCS.NS": ["tcs", "tata consultancy"],
    "HDFCBANK.NS": ["hdfc", "hdfc bank"],
    "ICICIBANK.NS": ["icici"],
    "INFY.NS": ["infosys"],
    "BHARTIARTL.NS": ["airtel", "bharti"],
    "SBIN.NS": ["sbi", "state bank of india"],
    "HINDUNILVR.NS": ["hul", "hindustan unilever"],
    "MARUTI.NS": ["maruti", "suzuki"],
    "WIPRO.NS": ["wipro"],
    "ADANIENT.NS": ["adani"],
    "LT.NS": ["larsen toubro", "l t"],
    "TITAN.NS": ["titan", "tanishq"],
    "DMART.NS": ["dmart", "avenue supermarts"],

    # --- BRVM (UEMOA) -----------------------------------------------------
    # La cote d'Abidjan est peu connue hors de la région : les alias y sont
    # d'autant plus utiles qu'un épargnant cherche « Sonatel », jamais
    # « SNTS ». Les filiales portent le nom du groupe et celui du pays.
    "SNTS.BRVM": ["sonatel", "orange senegal", "orange sn"],
    "ORAC.BRVM": ["orange cote d ivoire", "orange ci"],
    "ONTBF.BRVM": ["onatel", "orange burkina", "telecel"],
    "ETIT.BRVM": ["ecobank", "eti", "ecobank transnational"],
    "ECOC.BRVM": ["ecobank cote d ivoire", "ecobank ci"],
    "SGBC.BRVM": ["societe generale cote d ivoire", "sgbci", "socgen ci"],
    "BOAS.BRVM": ["bank of africa senegal", "boa senegal"],
    "BOAC.BRVM": ["bank of africa cote d ivoire", "boa ci"],
    "BOAB.BRVM": ["bank of africa benin", "boa benin"],
    "BOAM.BRVM": ["bank of africa mali", "boa mali"],
    "BOAN.BRVM": ["bank of africa niger", "boa niger"],
    "BOABF.BRVM": ["bank of africa burkina", "boa burkina"],
    "CBIBF.BRVM": ["coris bank", "coris"],
    "NSBC.BRVM": ["nsia banque", "nsia"],
    "ORGT.BRVM": ["oragroup", "orabank"],
    "CIEC.BRVM": ["cie", "compagnie ivoirienne d electricite"],
    "SDCC.BRVM": ["sodeci", "sode"],
    "NTLC.BRVM": ["nestle cote d ivoire", "nestle ci"],
    "UNLC.BRVM": ["unilever cote d ivoire", "unilever ci"],
    "TTLC.BRVM": ["totalenergies cote d ivoire", "total ci"],
    "TTLS.BRVM": ["totalenergies senegal", "total senegal"],
    "SHEC.BRVM": ["vivo energy", "shell cote d ivoire"],
    "SIVC.BRVM": ["erium", "air liquide cote d ivoire"],
    "PALC.BRVM": ["palmci", "palm cote d ivoire"],
    "SPHC.BRVM": ["saph", "societe africaine de plantations d heveas"],
    "SOGC.BRVM": ["sogb"],
    "SLBC.BRVM": ["solibra", "brasserie ivoirienne"],
    "STBC.BRVM": ["sitab", "tabac ivoirien"],
    "LNBB.BRVM": ["loterie nationale du benin", "lnb"],
    "SDSC.BRVM": ["africa global logistics", "bollore africa logistics", "agl"],
    "CFAC.BRVM": ["cfao motors", "cfao"],
    "UNXC.BRVM": ["uniwax", "pagne wax"],
    "FTSC.BRVM": ["filtisac"],
    "SMBC.BRVM": ["smb", "societe multinationale de bitumes"],
    "ABJC.BRVM": ["servair abidjan", "servair"],

    # --- Afrique australe -------------------------------------------------
    "NPN.JO": ["naspers"],
    "MTN.JO": ["mtn"],
    "SOL.JO": ["sasol"],
    "SHP.JO": ["shoprite"],
    "CPI.JO": ["capitec"],
}


def cle_recherche(societe):
    """La clé sur laquelle une valeur est trouvée.

    Le nom légal, le symbole, et les noms usuels — le tout dépouillé de
    ses accents.
    """
    morceaux = [societe.get("nom") or "", societe.get("ticker") or ""]
    morceaux += ALIAS.get(societe.get("ticker"), [])
    return sans_accents(" ".join(morceaux))
