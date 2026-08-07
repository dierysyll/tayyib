"""
L'univers couvert : les places de marché que Yahoo Finance documente assez
pour qu'un screening soit vérifiable.

Le produit est parti de la seule place de Paris, parce que Zoya et Musaffa,
les deux références du screening halal, sont anglophones et centrées sur
les valeurs américaines : un investisseur francophone qui détient un PEA
n'y trouvait pas ses valeurs. Ce manque reste la raison d'être de Tayyib,
et Paris reste la place de référence.

Mais un musulman francophone n'investit pas qu'à Paris. Il détient un PEA
et un compte-titres, il regarde Wall Street comme tout le monde, et il a
souvent une raison particulière de s'intéresser à Riyad, Istanbul, Kuala
Lumpur ou Casablanca. Couvrir ces places n'est pas de l'expansionnisme :
c'est la même promesse, tenue jusqu'au bout.

Quand la source ne suffit pas, on va la chercher ailleurs
---------------------------------------------------------
La **BRVM** d'Abidjan — la place commune aux huit pays de l'UEMOA — est
absente de Yahoo, et c'était l'absence la plus coûteuse : elle privait de
screening les épargnants pour qui ce produit a été écrit. Elle n'est plus
un trou. Nous la collectons directement auprès de la BRVM (voir
`data/brvm.py`), ce qui prouve au passage qu'une place manquante n'est pas
une fatalité : c'est un collecteur à écrire.

Restent celles où même la source primaire ne donne rien d'exploitable :

  - **Casablanca**, et il a fallu le vérifier pour s'en
    convaincre : Yahoo ne répond pas « symbole inconnu » sur les valeurs
    marocaines, il répond « Too Many Requests ». L'erreur laisse croire à
    une limitation de débit passagère, et donc à une place récupérable en
    réessayant. Elle ne l'est pas — interrogés en alternance à une seconde
    et demie d'intervalle, `AI.PA`, `SAP.DE` et `NESN.SW` répondent quand
    `ATW.CS`, `IAM.CS` et `BCP.CS` échouent systématiquement. Le suffixe
    `.CS` n'est tout simplement pas servi ;
  - **Tunis**, **Lagos**, **Mascate** et **Manama** sont dans le même cas,
    ou n'exposent qu'une cotation sans états financiers.

Casablanca reste donc la place manquante qui coûte le plus, et elle est
affichée telle quelle en Méthodologie plutôt que contournée. La Bourse de
Casablanca publie ses cotations sur son propre site : le jour où quelqu'un
écrira ce collecteur-là, elle rejoindra la BRVM.

Ces trous sont affichés dans l'interface (voir la page Méthodologie).
Prétendre à une couverture mondiale qu'on n'a pas serait exactement le
genre d'approximation que ce produit refuse.

Format des symboles
-------------------
Ce sont les symboles Yahoo Finance, suffixés par place (`.PA` Paris,
`.SR` Riyad, `.AE` Dubaï et Abu Dhabi réunis...). Les valeurs américaines
n'ont pas de suffixe.

Attention aux homonymes trompeurs : `TE.PA` est Technip Energies, pas
Teleperformance (qui est `TEP.PA`). Un symbole mal attribué produit un
verdict parfaitement cohérent sur la mauvaise société — c'est le genre
d'erreur qu'aucun test ne rattrape. `refresh.py` affiche le nom renvoyé
par Yahoo pour chaque symbole : c'est là qu'on vérifie.
"""

from data import brvm

# Les grands ensembles, dans l'ordre où ils sont proposés à l'utilisateur.
# L'Europe d'abord : c'est là que se trouve le lecteur visé, et son PEA.
REGIONS = {
    "europe": {
        "id": "europe",
        "nom": "Europe",
        "resume": "Le PEA et le compte-titres européen — Paris en tête.",
    },
    "ameriques": {
        "id": "ameriques",
        "nom": "Amériques",
        "resume": "Wall Street et Toronto, incontournables en compte-titres.",
    },
    "monde-musulman": {
        "id": "monde-musulman",
        "nom": "Monde musulman",
        "resume": "Golfe, Turquie, Asie du Sud-Est, Afrique du Nord, Pakistan.",
    },
    "asie-afrique": {
        "id": "asie-afrique",
        "nom": "Asie & Afrique",
        "resume": "Mumbai et Johannesburg, deux places profondes et bien documentées.",
    },
}


# --- Europe ---------------------------------------------------------------

PARIS = [
    # CAC 40
    "AC.PA", "AI.PA", "AIR.PA", "ALO.PA", "MT.AS", "CS.PA", "BNP.PA",
    "EN.PA", "CAP.PA", "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "EDEN.PA",
    "ENGI.PA", "EL.PA", "ERF.PA", "RMS.PA", "KER.PA", "LR.PA", "OR.PA",
    "MC.PA", "ML.PA", "ORA.PA", "RI.PA", "PUB.PA", "RNO.PA", "SAF.PA",
    "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "STLAP.PA", "STMPA.PA",
    "TEP.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA",
    # Reste du SBF 120
    "ADP.PA", "AF.PA", "AKE.PA", "ATE.PA", "AMUN.PA", "APAM.AS", "AYV.PA",
    "BIM.PA", "BOL.PA", "BVI.PA", "CLARI.PA", "COFA.PA", "COV.PA", "AM.PA",
    "DEC.PA", "ELIS.PA", "ERA.PA", "ETL.PA", "FGR.PA", "FR.PA", "FRVIA.PA",
    "GET.PA", "GFC.PA", "GTT.PA", "ICAD.PA", "IPN.PA", "ITP.PA", "LI.PA",
    "MERY.PA", "NK.PA", "NEX.PA", "NXI.PA", "OVH.PA", "PLX.PA", "OPM.PA",
    "RUI.PA", "RXL.PA", "SCR.PA", "SESG.PA", "SK.PA", "SOI.PA", "SOP.PA",
    "SPIE.PA", "SW.PA", "TE.PA", "TFI.PA", "TRI.PA", "UBI.PA", "VIRP.PA",
    "VIV.PA", "VK.PA", "VRLA.PA", "VU.PA", "WAVE.PA", "WLN.PA", "ATO.PA",
    "DIM.PA", "MAU.PA",
]

AMSTERDAM = [
    "ASML.AS", "INGA.AS", "ADYEN.AS", "HEIA.AS", "PHIA.AS", "AD.AS",
    "WKL.AS", "RAND.AS", "AKZA.AS", "DSFIR.AS", "KPN.AS", "NN.AS",
    "ASRNL.AS", "ABN.AS", "IMCD.AS", "BESI.AS", "LIGHT.AS", "PRX.AS",
    "UMG.AS", "EXO.AS", "HEIJM.AS", "VPK.AS", "AALB.AS", "ARCAD.AS",
    "SBMO.AS", "TWEKA.AS", "FUR.AS", "CRBN.AS",
]

BRUXELLES = [
    "ABI.BR", "KBC.BR", "UCB.BR", "SOLB.BR", "GBLB.BR", "AGS.BR",
    "COLR.BR", "UMI.BR", "PROX.BR", "WDP.BR", "ELI.BR", "ARGX.BR",
    "MELE.BR", "BEKB.BR", "DIE.BR", "ONTEX.BR", "TESB.BR", "LOTB.BR",
    "ACKB.BR", "SOF.BR", "BAR.BR", "AZE.BR",
]

ZURICH = [
    "NESN.SW", "NOVN.SW", "UBSG.SW", "ZURN.SW", "ABBN.SW", "CFR.SW",
    "LONN.SW", "SIKA.SW", "GIVN.SW", "SREN.SW", "ALC.SW", "SCMN.SW",
    "GEBN.SW", "HOLN.SW", "SLHN.SW", "BAER.SW", "PGHN.SW", "SOON.SW",
    "STMN.SW", "TEMN.SW", "LOGN.SW", "ADEN.SW", "KNIN.SW", "SGSN.SW",
    "VACN.SW", "EMSN.SW", "DKSH.SW", "SQN.SW", "BUCN.SW",
]

FRANCFORT = [
    "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "MUV2.DE", "MBG.DE", "BMW.DE",
    "VOW3.DE", "BAS.DE", "BAYN.DE", "RWE.DE", "EOAN.DE", "ADS.DE",
    "DHL.DE", "IFX.DE", "MRK.DE", "HEN3.DE", "DB1.DE", "VNA.DE",
    "HNR1.DE", "SY1.DE", "BEI.DE", "FRE.DE", "CON.DE", "HEI.DE",
    "PAH3.DE", "ZAL.DE", "SHL.DE", "ENR.DE", "QIA.DE", "LHA.DE",
    "TKA.DE", "EVK.DE", "BOSS.DE", "PUM.DE", "SRT3.DE", "WCH.DE",
    "1COV.DE", "RHM.DE", "DTG.DE", "BNR.DE", "KGX.DE", "LEG.DE",
    "CBK.DE", "DBK.DE", "AFX.DE", "JUN3.DE", "HLE.DE", "DUE.DE",
    "NEM.DE", "G24.DE", "AIR.DE", "TLX.DE",
]

LONDRES = [
    "SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "RIO.L", "GSK.L",
    "DGE.L", "BATS.L", "LSEG.L", "REL.L", "NG.L", "GLEN.L", "AAL.L",
    "BARC.L", "LLOY.L", "NWG.L", "VOD.L", "PRU.L", "TSCO.L", "IMB.L",
    "CPG.L", "EXPN.L", "RKT.L", "SGE.L", "BA.L", "ANTO.L",
    "SMIN.L", "WPP.L", "ITRK.L", "HLMA.L", "BNZL.L", "CRDA.L", "IHG.L",
    "JD.L", "MNDI.L", "NXT.L", "PSN.L", "SBRY.L", "SN.L", "SVT.L",
    "UU.L", "WTB.L", "STAN.L", "ABF.L", "ADM.L", "AV.L", "BKG.L", "DCC.L", "FRES.L", "HIK.L", "III.L", "INF.L", "LGEN.L",
    "LAND.L", "MKS.L", "PSON.L", "SDR.L", "SGRO.L", "SPX.L", "TW.L",
]

MILAN = [
    "ENI.MI", "ISP.MI", "UCG.MI", "ENEL.MI", "RACE.MI", "STLAM.MI",
    "G.MI", "TIT.MI", "MB.MI", "BAMI.MI", "LDO.MI", "PST.MI", "SRG.MI",
    "TRN.MI", "PIRC.MI", "MONC.MI", "CPR.MI", "A2A.MI", "BPE.MI",
    "REC.MI", "DIA.MI", "IG.MI", "AMP.MI", "BZU.MI", "ERG.MI", "IP.MI",
    "TEN.MI", "SPM.MI", "FBK.MI", "BC.MI", "CE.MI",
]

MADRID = [
    "ITX.MC", "IBE.MC", "SAN.MC", "BBVA.MC", "TEF.MC", "REP.MC",
    "AENA.MC", "FER.MC", "AMS.MC", "CLNX.MC", "ELE.MC", "NTGY.MC",
    "ACS.MC", "CABK.MC", "SAB.MC", "GRF.MC", "ANA.MC", "MAP.MC",
    "MRL.MC", "COL.MC", "ENG.MC", "RED.MC", "ACX.MC", "VIS.MC",
    "LOG.MC", "ROVI.MC", "SLR.MC", "IAG.MC", "MEL.MC", "BKT.MC",
    "UNI.MC", "CIE.MC",
]

LISBONNE = [
    "GALP.LS", "EDP.LS", "JMT.LS", "NOS.LS", "SON.LS", "EDPR.LS",
    "CTT.LS", "NVG.LS", "SEM.LS", "ALTR.LS", "COR.LS", "RENE.LS",
]

VIENNE = [
    "OMV.VI", "VOE.VI", "EBS.VI", "RBI.VI", "VIG.VI", "ANDR.VI",
    "WIE.VI", "BG.VI", "POST.VI", "LNZ.VI", "UQA.VI", "SBO.VI",
    "DOC.VI", "ATS.VI", "FACC.VI", "CAI.VI", "MMK.VI",
    "PAL.VI",
]

DUBLIN = ["RYA.IR", "KRZ.IR", "GL9.IR", "GVR.IR", "OIZ.IR", "C5H.IR"]

STOCKHOLM = [
    "VOLV-B.ST", "ATCO-A.ST", "INVE-B.ST", "ASSA-B.ST", "SEB-A.ST",
    "HM-B.ST", "ERIC-B.ST", "SAND.ST", "SHB-A.ST", "SWED-A.ST",
    "TELIA.ST", "ALFA.ST", "SKF-B.ST", "ESSITY-B.ST", "EVO.ST",
    "HEXA-B.ST", "NIBE-B.ST", "BOL.ST", "GETI-B.ST", "LIFCO-B.ST",
    "INDU-C.ST", "SECU-B.ST", "TEL2-B.ST", "SAAB-B.ST", "ELUX-B.ST",
    "HUSQ-B.ST", "SCA-B.ST", "SKA-B.ST", "TREL-B.ST", "KINV-B.ST",
    "EQT.ST", "LATO-B.ST", "ADDT-B.ST", "INDT.ST", "FABG.ST", "NDA-SE.ST",
]

COPENHAGUE = [
    "NOVO-B.CO", "DSV.CO", "MAERSK-B.CO", "CARL-B.CO", "VWS.CO",
    "COLO-B.CO", "GN.CO", "ORSTED.CO", "TRYG.CO", "DEMANT.CO",
    "PNDORA.CO", "ROCK-B.CO", "AMBU-B.CO", "ISS.CO", "NKT.CO", "DANSKE.CO", "GMAB.CO", "BAVA.CO", "RBREW.CO", "NSIS-B.CO",
]

OSLO = [
    "EQNR.OL", "DNB.OL", "TEL.OL", "NHY.OL", "MOWI.OL", "YAR.OL",
    "ORK.OL", "AKRBP.OL", "KOG.OL", "SALM.OL", "TOM.OL", "SUBC.OL",
    "STB.OL", "GJF.OL", "LSG.OL", "FRO.OL",
    "NOD.OL", "ELK.OL", "VEI.OL", "AKSO.OL", "TGS.OL",
    "NAS.OL", "AUSS.OL",
]

VARSOVIE = [
    "PKN.WA", "PKO.WA", "PEO.WA", "PZU.WA", "KGH.WA", "DNP.WA",
    "LPP.WA", "CDR.WA", "ALE.WA", "MBK.WA", "CPS.WA",
    "OPL.WA", "JSW.WA", "TPE.WA", "PGE.WA", "ENA.WA", "KTY.WA",
    "ATT.WA", "EUR.WA", "MIL.WA", "BDX.WA", "ALR.WA",
]


# --- Amériques ------------------------------------------------------------

NEW_YORK = [
    # Les mégacapitalisations, celles que tout le monde regarde
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "LLY", "AVGO", "JPM", "V", "XOM", "UNH", "MA", "PG", "JNJ", "COST",
    "HD", "ORCL", "ABBV", "CVX", "MRK", "KO", "ADBE", "PEP", "WMT",
    "CRM", "BAC", "TMO", "MCD", "CSCO", "ACN", "LIN", "ABT", "DHR",
    "NFLX", "AMD", "TXN", "WFC", "PM", "DIS", "INTC", "VZ", "INTU",
    "COP", "CAT", "IBM", "AMGN", "NOW", "GE", "QCOM", "UNP", "SPGI",
    "PFE", "HON", "NEE", "RTX", "LOW", "T", "BKNG", "ELV", "GS",
    "ISRG", "PLD", "BLK", "SYK", "MDT", "DE", "TJX", "VRTX", "LMT",
    "ADP", "MDLZ", "CVS", "REGN", "CI", "SCHW", "AXP", "BSX",
    "ZTS", "C", "CB", "MO", "ADI", "SO", "PGR", "ETN", "DUK",
    "BDX", "SLB", "MU", "EOG", "AON", "ITW", "APD", "KLAC", "LRCX",
    "NOC", "WM", "CSX", "EMR", "MCK", "PANW", "SNPS", "CDNS", "MAR",
    "PSA", "GD", "ORLY", "ROP", "MSI", "NSC", "PH", "AJG", "TT",
    "AZO", "ECL", "TDG", "MCO", "AFL", "PCAR", "CARR", "HLT", "NKE",
    "SBUX", "F", "GM", "UPS", "FDX", "PYPL", "UBER", "ABNB", "SHW",
    "CTAS", "DXCM", "IDXX", "ANET", "FTNT", "CRWD", "DDOG", "SNOW",
    "WDAY", "ADSK", "EA", "TTWO", "PLTR", "DELL", "HPQ", "WDC", "STX",
    "ON", "MCHP", "NXPI", "ARM", "COIN", "HOOD", "RBLX", "SMCI", "BA",
]

TORONTO = [
    "RY.TO", "TD.TO", "BNS.TO", "BMO.TO", "CM.TO", "ENB.TO", "CNQ.TO",
    "SU.TO", "TRP.TO", "CP.TO", "CNR.TO", "ATD.TO", "BCE.TO", "T.TO",
    "MFC.TO", "SLF.TO", "GWO.TO", "NA.TO", "FTS.TO", "EMA.TO", "PPL.TO",
    "TOU.TO", "IMO.TO", "CVE.TO", "WCP.TO", "ARX.TO", "NTR.TO",
    "AEM.TO", "WPM.TO", "FNV.TO", "K.TO", "TECK-B.TO", "CCO.TO",
    "SHOP.TO", "CSU.TO", "GIB-A.TO", "OTEX.TO", "DSG.TO", "L.TO",
    "MRU.TO", "QSR.TO", "DOL.TO", "WN.TO", "WSP.TO", "STN.TO",
    "TFII.TO", "CAE.TO", "ONEX.TO", "POW.TO", "IFC.TO", "FFH.TO",
    "H.TO", "AQN.TO",
]


# --- Monde musulman -------------------------------------------------------

RIYAD = [
    "2222.SR", "1120.SR", "2010.SR", "7010.SR", "1180.SR", "1211.SR",
    "1010.SR", "1050.SR", "1060.SR", "1150.SR", "1080.SR", "2380.SR",
    "2020.SR", "2290.SR", "4001.SR", "4190.SR", "4003.SR", "2280.SR",
    "6010.SR", "4002.SR", "4013.SR", "4004.SR", "2270.SR", "4161.SR",
    "7020.SR", "7030.SR", "4030.SR", "4200.SR", "2310.SR", "2330.SR",
    "3030.SR", "3020.SR", "3040.SR", "3050.SR", "3060.SR", "4300.SR",
    "4321.SR", "8010.SR", "8210.SR", "2350.SR", "2001.SR", "6001.SR",
    "4260.SR", "2060.SR", "1301.SR", "1320.SR", "2170.SR", "4110.SR",
]

DOHA = [
    "QNBK.QA", "IQCD.QA", "MARK.QA", "CBQK.QA", "QIBK.QA", "QEWS.QA",
    "ORDS.QA", "QGTS.QA", "MPHC.QA", "QAMC.QA", "BRES.QA", "QIIK.QA",
    "DHBK.QA", "ABQK.QA", "QFLS.QA", "QNCD.QA", "GWCS.QA", "MCCS.QA",
    "VFQS.QA", "QATI.QA", "SIIS.QA", "WDAM.QA", "BLDN.QA", "MERS.QA",
    "MKDM.QA", "IGRD.QA", "MEZA.QA", "QLMI.QA", "BEMA.QA", "AHCS.QA",
]

KOWEIT = [
    "NBK.KW", "KFH.KW", "ZAIN.KW", "BOUBYAN.KW", "GBK.KW",
    "MABANEE.KW", "HUMANSOFT.KW", "KIB.KW", "WARBABANK.KW", "JAZEERA.KW",
    "ALIMTIAZ.KW", "KPROJ.KW", "NIND.KW",
]

EMIRATS = [
    "EMAAR.AE", "EMIRATESNBD.AE", "DIB.AE", "AIRARABIA.AE", "AMANAT.AE", "SALIK.AE", "DEWA.AE",
    "TECOM.AE", "EMAARDEV.AE", "DU.AE",
    "DFM.AE", "TABREED.AE", "ARMX.AE",
]

ISTANBUL = [
    "THYAO.IS", "ASELS.IS", "BIMAS.IS", "AKBNK.IS", "GARAN.IS",
    "ISCTR.IS", "KCHOL.IS", "SAHOL.IS", "EREGL.IS", "TUPRS.IS",
    "FROTO.IS", "TOASO.IS", "SISE.IS", "PGSUS.IS", "TCELL.IS",
    "TTKOM.IS", "YKBNK.IS", "VAKBN.IS", "HALKB.IS", "ARCLK.IS",
    "PETKM.IS", "ENKAI.IS", "TAVHL.IS",
    "MGROS.IS", "ULKER.IS", "VESTL.IS", "HEKTS.IS", "SASA.IS",
    "ALARK.IS", "DOHOL.IS", "EKGYO.IS", "TKFEN.IS", "AKSEN.IS",
    "ZOREN.IS", "GUBRF.IS", "BRSAN.IS", "CIMSA.IS", "OYAKC.IS",
    "KRDMD.IS", "ISDMR.IS", "AGHOL.IS", "ASTOR.IS", "MAVI.IS",
    "CCOLA.IS", "AEFES.IS", "TTRAK.IS", "OTKAR.IS", "LOGO.IS",
]

KUALA_LUMPUR = [
    "1155.KL", "1023.KL", "1295.KL", "5225.KL", "6888.KL", "6033.KL",
    "5681.KL", "3816.KL", "4863.KL", "6012.KL", "6947.KL", "5347.KL",
    "3182.KL", "1961.KL", "2445.KL", "5285.KL", "4197.KL", "6742.KL",
    "4677.KL", "5183.KL", "7113.KL", "5168.KL", "7153.KL", "5296.KL",
    "1082.KL", "5819.KL", "1015.KL", "2488.KL", "1066.KL", "5148.KL",
    "8583.KL", "5211.KL", "5099.KL", "3034.KL", "4707.KL", "3689.KL",
    "7084.KL", "4715.KL",
]

JAKARTA = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK",
    "UNVR.JK", "ICBP.JK", "INDF.JK", "KLBF.JK", "GGRM.JK", "HMSP.JK",
    "UNTR.JK", "ADRO.JK", "PTBA.JK", "ITMG.JK", "ANTM.JK", "INCO.JK",
    "TINS.JK", "MDKA.JK", "SMGR.JK", "INTP.JK", "JPFA.JK", "CPIN.JK",
    "AMRT.JK", "MAPI.JK", "ACES.JK", "ERAA.JK", "TOWR.JK", "TBIG.JK",
    "EXCL.JK", "ISAT.JK", "PGAS.JK", "MEDC.JK", "AKRA.JK", "BRPT.JK",
    "TPIA.JK", "ESSA.JK", "MIKA.JK", "SIDO.JK", "BSDE.JK", "CTRA.JK",
    "SMRA.JK", "PWON.JK", "JSMR.JK", "GOTO.JK", "ARTO.JK",
]

LE_CAIRE = [
    "COMI.CA", "SWDY.CA", "TMGH.CA", "EAST.CA", "ETEL.CA", "ABUK.CA",
    "MFPC.CA", "SKPC.CA", "HRHO.CA", "ORAS.CA", "ISPH.CA", "EKHO.CA",
    "AMOC.CA", "ESRS.CA", "PHDC.CA", "HELI.CA", "OCDI.CA",
    "EGCH.CA", "CIEB.CA", "ADIB.CA", "FAITA.CA", "JUFO.CA", "DOMT.CA",
    "OLFI.CA", "CCAP.CA", "RAYA.CA", "BTFH.CA", "EFIH.CA",
]

KARACHI = [
    "LUCK.KA", "OGDC.KA", "PPL.KA", "POL.KA", "MARI.KA", "HUBC.KA",
    "ENGRO.KA", "EFERT.KA", "FFC.KA", "PSO.KA", "MCB.KA", "UBL.KA",
    "HBL.KA", "MEBL.KA", "BAHL.KA", "NBP.KA", "SYS.KA", "TRG.KA",
    "NESTLE.KA", "COLG.KA", "PAKT.KA", "DGKC.KA", "MLCF.KA",
    "CHCC.KA", "FCCL.KA", "KOHC.KA", "INDU.KA", "HCAR.KA", "ATLH.KA",
    "SEARL.KA", "AGP.KA", "HINOON.KA", "PIOC.KA", "THALL.KA", "ILP.KA",
    "SNGP.KA", "SSGC.KA", "ATRL.KA", "NRL.KA", "GATM.KA", "NML.KA",
    "KTML.KA", "AICL.KA",
]

# --- Asie & Afrique -------------------------------------------------------

MUMBAI = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "SBIN.NS", "LICI.NS", "ITC.NS", "HINDUNILVR.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "KOTAKBANK.NS", "AXISBANK.NS", "ADANIENT.NS", "ONGC.NS", "TITAN.NS",
    "NTPC.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "WIPRO.NS",
    "NESTLEIND.NS", "POWERGRID.NS", "M&M.NS",
    "JSWSTEEL.NS", "TATASTEEL.NS", "COALINDIA.NS", "BAJAJFINSV.NS",
    "ADANIPORTS.NS", "HDFCLIFE.NS", "SBILIFE.NS", "GRASIM.NS",
    "TECHM.NS", "INDUSINDBK.NS", "HINDALCO.NS", "DRREDDY.NS",
    "CIPLA.NS", "BRITANNIA.NS", "DIVISLAB.NS", "EICHERMOT.NS",
    "APOLLOHOSP.NS", "BPCL.NS", "TATACONSUM.NS", "HEROMOTOCO.NS",
    "SHRIRAMFIN.NS", "BAJAJ-AUTO.NS", "IOC.NS", "GAIL.NS", "VEDL.NS",
    "DLF.NS", "PIDILITIND.NS", "SIEMENS.NS", "HAVELLS.NS", "DABUR.NS",
    "GODREJCP.NS", "MARICO.NS", "AMBUJACEM.NS", "SHREECEM.NS",
    "TORNTPHARM.NS", "ZYDUSLIFE.NS", "LUPIN.NS", "AUROPHARMA.NS",
    "BIOCON.NS", "TRENT.NS", "DMART.NS", "PAGEIND.NS", "MUTHOOTFIN.NS",
    "CHOLAFIN.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "INDIGO.NS",
    "TVSMOTOR.NS", "HAL.NS", "BEL.NS", "BHEL.NS", "RECLTD.NS", "PFC.NS",
    "IRFC.NS", "IRCTC.NS", "NYKAA.NS", "POLICYBZR.NS",
]

JOHANNESBURG = [
    "NPN.JO", "SOL.JO", "FSR.JO", "SBK.JO", "ABG.JO", "NED.JO",
    "CPI.JO", "MTN.JO", "VOD.JO", "BID.JO", "BVT.JO", "SHP.JO",
    "CLS.JO", "WHL.JO", "TFG.JO", "MRP.JO", "SPP.JO", "AGL.JO",
    "BHG.JO", "IMP.JO", "SSW.JO", "GFI.JO", "HAR.JO",
    "ANG.JO", "EXX.JO", "KIO.JO", "ARI.JO", "OMU.JO", "SLM.JO",
    "DSY.JO", "GRT.JO", "RDF.JO", "HYP.JO", "APN.JO", "NTC.JO",
    "LHC.JO", "TBS.JO", "AVI.JO", "PIK.JO", "TRU.JO",
]


# --- Assemblage -----------------------------------------------------------
#
# Chaque place porte sa devise : elle sert à convertir les capitalisations
# en euros (voir data/fx.py) pour que le tri par taille ait un sens quand
# on mélange une roupie indonésienne et un franc suisse.

PLACES = {
    # Europe
    "paris": {
        "nom": "Paris", "pays": "France", "code": "FR", "devise": "EUR",
        "region": "europe", "indice": "CAC 40 · SBF 120",
        "note": "La place de référence de Tayyib, et la seule éligible au PEA.",
        "valeurs": PARIS,
    },
    "amsterdam": {
        "nom": "Amsterdam", "pays": "Pays-Bas", "code": "NL", "devise": "EUR",
        "region": "europe", "indice": "AEX", "valeurs": AMSTERDAM,
    },
    "bruxelles": {
        "nom": "Bruxelles", "pays": "Belgique", "code": "BE", "devise": "EUR",
        "region": "europe", "indice": "BEL 20", "valeurs": BRUXELLES,
    },
    "zurich": {
        "nom": "Zurich", "pays": "Suisse", "code": "CH", "devise": "CHF",
        "region": "europe", "indice": "SMI", "valeurs": ZURICH,
    },
    "francfort": {
        "nom": "Francfort", "pays": "Allemagne", "code": "DE", "devise": "EUR",
        "region": "europe", "indice": "DAX · MDAX", "valeurs": FRANCFORT,
    },
    "londres": {
        "nom": "Londres", "pays": "Royaume-Uni", "code": "GB", "devise": "GBp",
        "region": "europe", "indice": "FTSE 100", "valeurs": LONDRES,
    },
    "milan": {
        "nom": "Milan", "pays": "Italie", "code": "IT", "devise": "EUR",
        "region": "europe", "indice": "FTSE MIB", "valeurs": MILAN,
    },
    "madrid": {
        "nom": "Madrid", "pays": "Espagne", "code": "ES", "devise": "EUR",
        "region": "europe", "indice": "IBEX 35", "valeurs": MADRID,
    },
    "lisbonne": {
        "nom": "Lisbonne", "pays": "Portugal", "code": "PT", "devise": "EUR",
        "region": "europe", "indice": "PSI", "valeurs": LISBONNE,
    },
    "vienne": {
        "nom": "Vienne", "pays": "Autriche", "code": "AT", "devise": "EUR",
        "region": "europe", "indice": "ATX", "valeurs": VIENNE,
    },
    "dublin": {
        "nom": "Dublin", "pays": "Irlande", "code": "IE", "devise": "EUR",
        "region": "europe", "indice": "ISEQ", "valeurs": DUBLIN,
    },
    "stockholm": {
        "nom": "Stockholm", "pays": "Suède", "code": "SE", "devise": "SEK",
        "region": "europe", "indice": "OMXS30", "valeurs": STOCKHOLM,
    },
    "copenhague": {
        "nom": "Copenhague", "pays": "Danemark", "code": "DK", "devise": "DKK",
        "region": "europe", "indice": "OMXC25", "valeurs": COPENHAGUE,
    },
    "oslo": {
        "nom": "Oslo", "pays": "Norvège", "code": "NO", "devise": "NOK",
        "region": "europe", "indice": "OBX", "valeurs": OSLO,
    },
    "varsovie": {
        "nom": "Varsovie", "pays": "Pologne", "code": "PL", "devise": "PLN",
        "region": "europe", "indice": "WIG20", "valeurs": VARSOVIE,
    },

    # Amériques
    "new-york": {
        "nom": "New York", "pays": "États-Unis", "code": "US", "devise": "USD",
        "region": "ameriques", "indice": "S&P 500 · Nasdaq",
        "note": "La place la mieux couverte au monde, et celle où les screeners concurrents s'arrêtent.",
        "valeurs": NEW_YORK,
    },
    "toronto": {
        "nom": "Toronto", "pays": "Canada", "code": "CA", "devise": "CAD",
        "region": "ameriques", "indice": "S&P/TSX",
        "note": "Utile aux francophones du Québec.",
        "valeurs": TORONTO,
    },

    # Monde musulman
    #
    # La BRVM ouvre la région, et non par courtoisie : c'est la seule place
    # où un épargnant de l'UEMOA achète dans sa propre monnaie, sans compte
    # à l'étranger. Elle est aussi la seule que nous collectons nous-mêmes.
    "brvm": {
        "nom": "BRVM (Abidjan)", "pays": "UEMOA — huit pays d'Afrique de l'Ouest",
        "code": "UEMOA", "devise": "XOF",
        "region": "monde-musulman", "indice": "BRVM Composite · BRVM 30",
        "source": "brvm",
        "note": "Place absente de Yahoo Finance : nous la collectons directement "
                "auprès de la BRVM. Les cours sont à jour ; les états financiers "
                "ne sont pas encore lus, si bien que les valeurs dont l'activité "
                "ne tranche pas restent « à vérifier ».",
        "valeurs": brvm.tickers(),
    },
    "riyad": {
        "nom": "Riyad", "pays": "Arabie saoudite", "code": "SA", "devise": "SAR",
        "region": "monde-musulman", "indice": "Tadawul · TASI",
        "note": "La plus grande place du monde musulman, et la mieux documentée par Yahoo.",
        "valeurs": RIYAD,
    },
    "doha": {
        "nom": "Doha", "pays": "Qatar", "code": "QA", "devise": "QAR",
        "region": "monde-musulman", "indice": "QE Index", "valeurs": DOHA,
    },
    "koweit": {
        "nom": "Koweït", "pays": "Koweït", "code": "KW", "devise": "KWD",
        "region": "monde-musulman", "indice": "Boursa Kuwait", "valeurs": KOWEIT,
    },
    "emirats": {
        "nom": "Dubaï & Abu Dhabi", "pays": "Émirats arabes unis", "code": "AE",
        "devise": "AED", "region": "monde-musulman", "indice": "DFM · ADX",
        "note": "Yahoo réunit les deux places sous le suffixe .AE ; la couverture est inégale.",
        "valeurs": EMIRATS,
    },
    "istanbul": {
        "nom": "Istanbul", "pays": "Turquie", "code": "TR", "devise": "TRY",
        "region": "monde-musulman", "indice": "BIST 100", "valeurs": ISTANBUL,
    },
    "kuala-lumpur": {
        "nom": "Kuala Lumpur", "pays": "Malaisie", "code": "MY", "devise": "MYR",
        "region": "monde-musulman", "indice": "FTSE Bursa Malaysia KLCI",
        "note": "Le pays où la finance islamique est la plus institutionnalisée.",
        "valeurs": KUALA_LUMPUR,
    },
    "jakarta": {
        "nom": "Jakarta", "pays": "Indonésie", "code": "ID", "devise": "IDR",
        "region": "monde-musulman", "indice": "IDX Composite",
        "note": "Le plus grand pays musulman du monde par la population.",
        "valeurs": JAKARTA,
    },
    "le-caire": {
        "nom": "Le Caire", "pays": "Égypte", "code": "EG", "devise": "EGP",
        "region": "monde-musulman", "indice": "EGX 30",
        "note": "Yahoo ne renseigne pas le secteur d'activité : ces valeurs tombent en « à vérifier ».",
        "valeurs": LE_CAIRE,
    },
    "karachi": {
        "nom": "Karachi", "pays": "Pakistan", "code": "PK", "devise": "PKR",
        "region": "monde-musulman", "indice": "KSE 100",
        "note": "Yahoo ne renseigne pas le secteur d'activité : ces valeurs tombent en « à vérifier ».",
        "valeurs": KARACHI,
    },
    # Asie & Afrique
    "mumbai": {
        "nom": "Mumbai", "pays": "Inde", "code": "IN", "devise": "INR",
        "region": "asie-afrique", "indice": "NIFTY 50",
        "note": "Deuxième population musulmane du monde.",
        "valeurs": MUMBAI,
    },
    "johannesburg": {
        "nom": "Johannesburg", "pays": "Afrique du Sud", "code": "ZA", "devise": "ZAR",
        "region": "asie-afrique", "indice": "JSE Top 40", "valeurs": JOHANNESBURG,
    },
}


# Les places que nous aimerions couvrir et que la source ne permet pas.
# Elles sont affichées telles quelles dans la page Méthodologie : une
# absence annoncée vaut mieux qu'une absence constatée par l'utilisateur.
PLACES_ABSENTES = [
    {
        "nom": "Casablanca", "code": "MA", "pays": "Maroc",
        "raison": "Le suffixe `.CS` n'est pas servi par Yahoo Finance. "
                  "La source ne le dit pas franchement — elle répond « Too Many "
                  "Requests », ce qui ressemble à une limitation passagère. "
                  "Vérification faite en alternant valeurs marocaines et "
                  "européennes dans une même session : les secondes répondent, "
                  "les premières jamais. Nous préférons retirer la place plutôt "
                  "que d'afficher un Maroc perpétuellement vide.",
    },
    {
        "nom": "Tunis", "code": "TN", "pays": "Tunisie",
        "raison": "Place absente de Yahoo Finance.",
    },
    {
        "nom": "Lagos", "code": "NG", "pays": "Nigeria",
        "raison": "Place absente de Yahoo Finance.",
    },
    {
        "nom": "Mascate & Manama", "code": "OM·BH", "pays": "Oman, Bahreïn",
        "raison": "Cotations partielles, sans états financiers exploitables.",
    },
]


def tickers():
    """Tous les symboles de l'univers, à plat — l'ordre est celui des places.

    Dédoublonné : une valeur cotée sur deux places de la liste (ou saisie
    deux fois par inadvertance) ne doit être collectée qu'une fois.
    """
    vus, plats = set(), []
    for place in PLACES.values():
        for ticker in place["valeurs"]:
            if ticker not in vus:
                vus.add(ticker)
                plats.append(ticker)
    return plats


def place_par_ticker():
    """Index symbole → identifiant de place, pour étiqueter la collecte."""
    return {
        ticker: place_id
        for place_id, place in PLACES.items()
        for ticker in place["valeurs"]
    }


def devises():
    """Les devises distinctes de l'univers — ce que data/fx.py doit convertir."""
    return sorted({place["devise"] for place in PLACES.values()})


def places_par_region():
    """Les places groupées par région, dans l'ordre de déclaration."""
    groupes = {region_id: [] for region_id in REGIONS}
    for place_id, place in PLACES.items():
        groupes[place["region"]].append(dict(place, id=place_id))
    return [
        dict(REGIONS[region_id], places=places)
        for region_id, places in groupes.items()
    ]


# Rétrocompatibilité : refresh.py et les scripts existants attendaient une
# liste plate nommée UNIVERSE.
UNIVERSE = tickers()
