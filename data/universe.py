"""
L'univers couvert : les grandes valeurs de la place de Paris.

C'est le choix de positionnement du produit. Zoya et Musaffa, les deux
références du screening halal, sont anglophones et centrées sur les
valeurs américaines. Un investisseur francophone qui détient un PEA n'y
trouve pas ses valeurs. On commence donc par là où le manque est réel :
Euronext Paris.

Les tickers sont au format Yahoo Finance (suffixe `.PA` pour Paris,
`.AS` pour Amsterdam quand la cotation principale y est).
"""

# CAC 40 et quelques grandes valeurs du SBF 120 qui reviennent souvent
# dans les portefeuilles particuliers.
UNIVERSE = [
    "AC.PA",     # Accor
    "AI.PA",     # Air Liquide
    "AIR.PA",    # Airbus
    "ALO.PA",    # Alstom
    "MT.AS",     # ArcelorMittal
    "CS.PA",     # AXA
    "BNP.PA",    # BNP Paribas
    "EN.PA",     # Bouygues
    "CAP.PA",    # Capgemini
    "CA.PA",     # Carrefour
    "ACA.PA",    # Crédit Agricole
    "BN.PA",     # Danone
    "DSY.PA",    # Dassault Systèmes
    "EDEN.PA",   # Edenred
    "ENGI.PA",   # Engie
    "EL.PA",     # EssilorLuxottica
    "ERF.PA",    # Eurofins Scientific
    "RMS.PA",    # Hermès
    "KER.PA",    # Kering
    "LR.PA",     # Legrand
    "OR.PA",     # L'Oréal
    "MC.PA",     # LVMH
    "ML.PA",     # Michelin
    "ORA.PA",    # Orange
    "RI.PA",     # Pernod Ricard
    "PUB.PA",    # Publicis
    "RNO.PA",    # Renault
    "SAF.PA",    # Safran
    "SGO.PA",    # Saint-Gobain
    "SAN.PA",    # Sanofi
    "SU.PA",     # Schneider Electric
    "GLE.PA",    # Société Générale
    "STLAP.PA",  # Stellantis
    "STMPA.PA",  # STMicroelectronics
    "TE.PA",     # Teleperformance
    "HO.PA",     # Thales
    "TTE.PA",    # TotalEnergies
    "URW.PA",    # Unibail-Rodamco-Westfield
    "VIE.PA",    # Veolia
    "DG.PA",     # Vinci
    "VIV.PA",    # Vivendi
    "WLN.PA",    # Worldline
    "ATO.PA",    # Atos
    "SW.PA",     # Sodexo
    "GTT.PA",    # GTT
    "IPN.PA",    # Ipsen
    "NEX.PA",    # Nexans
    "RXL.PA",    # Rexel
    "SOI.PA",    # Soitec
    "TFI.PA",    # TF1
    "UBI.PA",    # Ubisoft
    "VRLA.PA",   # Verallia
    "AYV.PA",    # Ayvens
    "AKE.PA",    # Arkema
    "BVI.PA",    # Bureau Veritas
    "COFA.PA",   # Coface
    "ELIS.PA",   # Elis
    "FGR.PA",    # Eiffage
    "GET.PA",    # Getlink
    "SESG.PA",   # SES
]
