# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) ·
Versioning: [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-14
### Added
- Live ADS bridge client/server (`pb.py`, `scripts/ads_live_server.py`).
- Simulation helper for `hpeesofsim` with unique run tags (`scripts/ads_sim_helper.py`).
- Evaluators: PA metric evaluator (`eval_var.py`), impedance-space evaluator (`eval_fomn.py`).
- Optimisers: pattern search with rejection-based hard floors
  (`pyopt_pa1_po39.py`, `pyopt_fomn_s2b.py`; an earlier random-search variant is kept for reference).
- EM driver stubs and CLIs (`run_mom.py`, `run_em_cli.py`).
- Central, environment-driven configuration (`scripts/config.py`) + `env.example`.
- Documentation set: environment, driving ADS, simulation, optimisation, EM co-simulation,
  figures, domain notes, pitfalls, project-status template.
- Minimal examples: netlist dump and patch-and-simulate (with a sweep-coverage guard).
### Notes
- Verified on Windows with ADS 2025 Update 2. ADS's private Python APIs are version-bound.
