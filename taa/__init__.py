"""
Ashcroft University Endowment — tactical asset allocation study.

Built for this study, in this folder, with no dependency on anything else on
the machine it was written on. Standard scientific Python only (pandas, numpy,
scipy) plus yfinance for the one-off price pull.

Module map, and who owns what:

  config       The study window and the mandate constants. One source of truth.
  _rawstore    PRIVATE. The raw cache. Only pitdata may read it.
  pitdata      THE CHOKE POINT. Every historical read passes through here with
               an as-of date. IPS 4.4.
  datapull     Ingestion. The only module that touches the network.

  costs        Implementation & Operations desk: transaction costs, corridors.
  signals      Quantitative desk: signal construction and standardisation.
  riskmodel    Quantitative desk: covariance, shrinkage, ex-ante tracking error.
  optimiser    Quantitative desk: the constrained allocation.
  regime       Macro desk: point-in-time regime read.
  compliance   Risk desk: the pass/fail test. Holds a veto, not an opinion.

  simulate     Office of the CIO: the five-year quarterly simulation, which
               emits the decision record as data.
  report_build Office of the CIO: renders the report, record and dashboard.
"""

__version__ = "1.0.0"
