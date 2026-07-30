"""
taa.exclusions — vehicle-level evidence for the board exclusions at IPS 3.5.

WHY THIS IS A SEPARATE FILE
------------------------------------------------------------------------------
IPS 3.5 assesses the board exclusions at the vehicle level and requires that a
broad index vehicle carrying incidental excluded exposure be "disclosed rather
than deemed compliant by silence". That is a question of fact about what a fund
holds, not a question about the test. Keeping the evidence here means it can be
re-sourced, re-dated and challenged without anyone touching taa/compliance.py,
and it means the compliance test itself asserts nothing about a holding that is
not written down with a source and a date.

METHOD, AND ITS LIMITS
------------------------------------------------------------------------------
Every weight below was read from the fund's own SEC Form N-PORT portfolio
schedule on EDGAR, which is public and free. Issuer websites and the commercial
holdings aggregators were either blocked or truncated, so N-PORT is the sole
holdings authority here. Weights are pctVal, the percentage of net assets, at
the stated period end.

Three limitations, stated rather than buried.

1. The totals are floors. A name below roughly 0.001% of the fund can be missed
   by the scan, so a vehicle recorded here at 0.66% tobacco may carry slightly
   more and cannot carry materially less.

2. GENERATION IS NOT EXTRACTION, AND THE MANDATE DOES NOT SAY WHICH IT MEANS.
   Several vehicles hold no coal miner and hold regulated or merchant utilities
   that still burn thermal coal. SPY holds seventeen such utilities. LQD holds
   roughly 1.2% in utility obligors that still burn coal. HYG holds 1.25% in
   NRG Energy and Talen Energy Supply. Whether the Board's exclusion reaches a
   generator that burns coal or only an extractor that mines it is a question
   about the Board's intent, and the risk function does not get to decide it.
   These rows are recorded with exclusion="thermal coal" and a note saying
   plainly that they are generation rather than extraction, so the disclosure
   puts the question in front of the Committee rather than resolving it
   silently in either direction. Resolving it is an IPS 2.3 amendment question.

3. The fuel mix of each utility, meaning what share of its generation is
   actually thermal coal, was NOT verified. Establishing materiality would
   require each issuer's own generation disclosure. Every generation row is
   therefore marked verified=False on the coal question even where the holding
   itself is verified, because what is unverified is the thing that would make
   the holding relevant.

THREE FALSE POSITIVES DELIBERATELY EXCLUDED
------------------------------------------------------------------------------
Anglo American and Teck, held in EFA and VEA, are metallurgical coal. Anglo
agreed to sell that business to Dhilmar in May 2026 and had exited thermal coal
earlier. Metallurgical coal makes steel and is not thermal coal, so neither is
recorded as a thermal coal exposure.

Vale, held in EEM and VWO at a weight large enough to matter, is iron ore. It
is not recorded.

Reynolds Consumer Products, held in VTI, makes food wrap and is unrelated to
Reynolds American. It is not recorded as tobacco.

Naming what was looked at and rejected matters as much as naming what was
found, because a screen that only ever adds names is a screen nobody has
audited.
"""

from __future__ import annotations

SOURCES = {
    "N-PORT": (
        "SEC Form N-PORT monthly portfolio schedule, primary_doc.xml, retrieved "
        "from EDGAR and parsed locally. Public filing, no subscription (IPS 4.4)."
    ),
    "10-Q": "SEC Form 10-Q, schedule of investments. Public filing.",
    "Slickcharts": (
        "Slickcharts S&P 500 component weights, fetched 28 July 2026, used only "
        "to cross-check the SPY N-PORT figures."
    ),
    "mining.com": (
        "Trade press, cited only for the status of BHP's Mt Arthur thermal coal "
        "operation and its targeted FY2030 closure."
    ),
}

# Each row becomes one taa.compliance.IncidentalExposure.
#   approx_weight is a fraction of the vehicle's net assets, not of the fund.
#   verified is True only where the holding was read from a filing AND the
#   holding on its own establishes the exposure.
ROWS = (
    # ---------------------------------------------------------------- tobacco
    {
        "vehicle": "SPY", "exclusion": "tobacco",
        "issuers": ("Philip Morris International 0.4600%", "Altria 0.1984%"),
        "approx_weight": 0.00658, "verified": True,
        "source": "N-PORT period 2026-03-31, 503 holdings; cross-checked against "
                  "Slickcharts S&P 500 weights",
        "as_of": "2026-03-31",
        "note": "Cross-check agreed to within one basis point on both names.",
    },
    {
        "vehicle": "VTI", "exclusion": "tobacco",
        "issuers": ("Philip Morris International 0.4104%", "Altria 0.1759%",
                    "Turning Point Brands 0.0025%", "Universal Corp 0.0020%"),
        "approx_weight": 0.00591, "verified": True,
        "source": "N-PORT period 2026-03-31, 3,524 holdings",
        "as_of": "2026-03-31",
        "note": "Reynolds Consumer Products was examined and excluded as packaging.",
    },
    {
        "vehicle": "EFA", "exclusion": "tobacco",
        "issuers": ("British American Tobacco 0.5905%", "Japan Tobacco 0.2057%",
                    "Imperial Brands 0.1325%"),
        "approx_weight": 0.00929, "verified": True,
        "source": "N-PORT period 2026-04-30, 710 holdings",
        "as_of": "2026-04-30",
        "note": "The heaviest equity tobacco weight in the opportunity set.",
    },
    {
        "vehicle": "VEA", "exclusion": "tobacco",
        "issuers": ("British American Tobacco 0.4192%", "Japan Tobacco 0.1442%",
                    "Imperial Brands 0.1035%", "KT&G 0.0366%",
                    "Scandinavian Tobacco 0.0018%"),
        "approx_weight": 0.00705, "verified": True,
        "source": "N-PORT period 2026-03-31, 3,945 holdings",
        "as_of": "2026-03-31",
        "note": "FTSE classes Korea as developed, so KT&G sits here rather than in VWO.",
    },
    {
        "vehicle": "EEM", "exclusion": "tobacco",
        "issuers": ("KT&G 0.0907%", "ITC Ltd 0.0716%", "Smoore International 0.0171%"),
        "approx_weight": 0.00179, "verified": True,
        "source": "N-PORT period 2026-05-31, 1,251 holdings",
        "as_of": "2026-05-31",
        "note": "",
    },
    {
        "vehicle": "VWO", "exclusion": "tobacco",
        "issuers": ("ITC Ltd 0.0868%", "Smoore International 0.0190%", "RLX 0.0126%",
                    "China Tobacco International HK 0.0063%", "Gudang Garam 0.0035%",
                    "BAT Malaysia 0.0014%"),
        "approx_weight": 0.00130, "verified": True,
        "source": "N-PORT period 2026-04-30, 6,411 holdings",
        "as_of": "2026-04-30",
        "note": "MSCI and FTSE differ on Korea, so KT&G appears in EEM and not here.",
    },
    {
        "vehicle": "LQD", "exclusion": "tobacco",
        "issuers": ("Philip Morris International, 24 bonds, 0.6116%",
                    "BAT Capital, 15 bonds, 0.4391%", "Altria, 10 bonds, 0.3120%",
                    "Reynolds American, 2 bonds, 0.0731%"),
        "approx_weight": 0.01436, "verified": True,
        "source": "N-PORT period 2026-05-31, 3,137 bond lines",
        "as_of": "2026-05-31",
        "note": "The largest tobacco weight of any vehicle in the opportunity set, and "
                "the one least likely to be anticipated, since a bond index screens on "
                "issuance rather than on market capitalisation. Imperial Brands Finance "
                "was searched for and is not present in this filing.",
    },

    # ----------------------------------------------------- thermal coal, mined
    {
        "vehicle": "EFA", "exclusion": "thermal coal",
        "issuers": ("Glencore 0.3571%", "BHP 0.9252%", "Mitsubishi 0.4752%",
                    "Itochu 0.3386%", "Sumitomo 0.1864%", "Idemitsu Kosan 0.0302%"),
        "approx_weight": None, "verified": True,
        "source": "N-PORT period 2026-04-30; BHP Mt Arthur status from mining.com 2026",
        "as_of": "2026-04-30",
        "note": "Glencore is the largest seaborne thermal coal exporter. BHP still "
                "operates Mt Arthur with closure targeted FY2030. The Japanese trading "
                "houses hold coal interests inside diversified groups, so the holding is "
                "verified while the share of each group attributable to thermal coal is "
                "not. Anglo American at 0.2552% was examined and excluded as "
                "metallurgical.",
    },
    {
        "vehicle": "VEA", "exclusion": "thermal coal",
        "issuers": ("BHP 0.6081%", "Mitsubishi 0.3859%", "Itochu 0.2741%",
                    "Glencore 0.2730%", "Sumitomo 0.1297%", "Whitehaven Coal 0.0171%",
                    "J-Power 0.0152%", "TransAlta 0.0122%", "Yancoal Australia 0.0075%",
                    "New Hope 0.0068%", "Korea Electric Power 0.0251%"),
        "approx_weight": None, "verified": True,
        "source": "N-PORT period 2026-03-31",
        "as_of": "2026-03-31",
        "note": "Whitehaven, Yancoal and New Hope are pure thermal coal producers. Teck "
                "at 0.0854% and Anglo American at 0.1567% were examined and excluded as "
                "metallurgical or exited.",
    },
    {
        "vehicle": "EEM", "exclusion": "thermal coal",
        "issuers": ("China Shenhua 0.1726%", "Coal India 0.0704%", "Yankuang 0.0559%",
                    "Adani Enterprises 0.0390%", "China Coal Energy 0.0236%",
                    "Inner Mongolia Yitai 0.0208%", "Shaanxi Coal 0.0174%",
                    "Bumi Resources Minerals 0.0146%", "Henan Shenhuo 0.0050%"),
        "approx_weight": 0.0042, "verified": True,
        "source": "N-PORT period 2026-05-31, 1,251 holdings",
        "as_of": "2026-05-31",
        "note": "Coal producers on an extraction basis. Vale at 0.4637% was examined and "
                "excluded as iron ore.",
    },
    {
        "vehicle": "VWO", "exclusion": "thermal coal",
        "issuers": ("China Shenhua 0.2092%", "Coal India 0.1003%", "Yankuang 0.0686%",
                    "Adani Enterprises 0.0573%", "China Coal 0.0458%",
                    "Bumi Resources 0.0409%", "Exxaro 0.0269%", "Adaro 0.0230%",
                    "Shaanxi Coal 0.0215%", "Inner Mongolia Yitai 0.0204%",
                    "Banpu 0.0120%", "and roughly fifteen smaller Chinese A-share "
                    "coal names"),
        "approx_weight": 0.0064, "verified": True,
        "source": "N-PORT period 2026-04-30, 6,411 holdings",
        "as_of": "2026-04-30",
        "note": "The broadest coal exposure of any vehicle examined, and a floor rather "
                "than a total, because the long tail of small A-share names was not "
                "enumerated exhaustively.",
    },
    {
        "vehicle": "VTI", "exclusion": "thermal coal",
        "issuers": ("Core Natural Resources 0.0080%", "Warrior Met 0.0079%",
                    "Peabody Energy 0.0064%", "Alpha Metallurgical 0.0034%",
                    "Ramaco 0.0012%", "Hallador 0.0008%"),
        "approx_weight": 0.00028, "verified": True,
        "source": "N-PORT period 2026-03-31",
        "as_of": "2026-03-31",
        "note": "De minimis at roughly three basis points of the vehicle. The filing "
                "still names CONSOL Energy, which merged with Arch into Core Natural "
                "Resources in January 2025, so the filed name is stale while the holding "
                "is real. Warrior Met and Alpha Metallurgical are principally "
                "metallurgical and are disclosed here for completeness rather than "
                "asserted as thermal.",
    },

    # ------------------------------------------- thermal coal, burned not mined
    {
        "vehicle": "SPY", "exclusion": "thermal coal",
        "issuers": ("Southern 0.1898%", "Duke 0.1822%", "AEP 0.1268%", "Dominion 0.0944%",
                    "Entergy 0.0909%", "Exelon 0.0897%", "Vistra 0.0859%", "Xcel 0.0843%",
                    "WEC 0.0675%", "NRG 0.0556%", "DTE 0.0542%", "Ameren 0.0543%",
                    "PPL 0.0504%", "CenterPoint 0.0503%", "FirstEnergy 0.0470%",
                    "Evergy 0.0339%", "Alliant 0.0328%"),
        "approx_weight": None, "verified": False,
        "source": "N-PORT period 2026-03-31, holdings verified; fuel mix NOT verified",
        "as_of": "2026-03-31",
        "note": "SPY holds no coal producer of any kind. These are seventeen utilities "
                "that still burn thermal coal. The holdings are verified and the share "
                "of each utility's generation that is coal is not, so materiality is "
                "unestablished. Whether the Board's exclusion reaches a generator that "
                "burns coal or only an extractor that mines it is a question of the "
                "Board's intent, and the risk function does not decide it. Put to the "
                "Committee under IPS 2.3.",
    },
    {
        "vehicle": "LQD", "exclusion": "thermal coal",
        "issuers": ("Duke complex 0.416%", "Southern and Georgia Power 0.259%",
                    "BHP Billiton Finance USA 0.2736%", "DTE 0.0916%",
                    "Entergy Louisiana 0.0830%", "Vistra Operations 0.0696%",
                    "Xcel 0.0677%", "Ameren 0.0379%", "PPL 0.0300%", "AEP 0.0236%",
                    "FirstEnergy 0.0148%"),
        "approx_weight": None, "verified": False,
        "source": "N-PORT period 2026-05-31, obligors verified; fuel mix NOT verified",
        "as_of": "2026-05-31",
        "note": "No coal-mining issuer. Roughly 1.2% of the fund sits in utility obligors "
                "that still burn coal, plus BHP Billiton Finance USA, which is the "
                "financing arm of a group that still operates Mt Arthur. Same intent "
                "question as SPY.",
    },
    {
        "vehicle": "HYG", "exclusion": "thermal coal",
        "issuers": ("NRG Energy, 12 bonds, 0.9748%",
                    "Talen Energy Supply, 2 bonds, 0.2776%"),
        "approx_weight": 0.01252, "verified": False,
        "source": "N-PORT period 2026-05-31, obligors verified; fuel mix NOT verified",
        "as_of": "2026-05-31",
        "note": "No coal-mining issuer and zero tobacco. A substring scan of every issuer "
                "name for tobacco returned nothing, which is worth stating because the "
                "expectation running into this work was that a high yield index would "
                "carry tobacco paper and it does not. Alliant Holdings and Tallgrass NRG "
                "were examined and excluded as insurance and midstream respectively.",
    },
)

# Vehicles examined and found to carry neither exclusion. Recorded so that a
# clean result is evidence of having looked rather than evidence of not looking.
CLEAN = {
    "VNQ": "N-PORT period 2026-04-30, 158 holdings. All real estate investment trusts "
           "and real estate operating companies. Zero tobacco, zero coal.",
    "IEF": "N-PORT period 2026-05-31, 16 holdings. Fifteen US Treasury notes and one "
           "cash sweep fund. Government paper only.",
    "BIL": "N-PORT period 2026-03-31, 23 holdings. Twenty US Treasury bills and three "
           "repurchase and cash lines.",
    "DBC": "Form 10-Q period 2026-03-31. Exchange-traded commodity futures and Treasury "
           "collateral. The strings coal and tobacco appear zero times in the filing.",
}
