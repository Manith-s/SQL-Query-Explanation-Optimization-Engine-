# Changelog

## [1.0.0] - 2025-08-14
- Features: smarter advisor scoring/filtering; workload mode; plan diff; parallel what-if with early stop; markdown/templated NL fallback
- Infra: Dockerized API+DB (HypoPG), health checks, metrics (gated)
- CLI: `--table`, `--markdown`, `--diff`, `--what-if`, `workload`
- Docs & CI: guides, tests, release workflows
- Migration/compat: additive fields only; no breaking changes

## v0.6.0
- Optional Prometheus metrics endpoint (`/metrics`) with bounded labels
- Rich OpenAPI examples for `/optimize` and minimal for `/explain`
- Benchmark micro-suite (opt-in) producing JSON/CSV reports
- Version bump to 0.6.0 and propagated in API

## v0.5.0
- Phase 4 optimization engine (rewrite + index advisor) implemented
- Deterministic outputs with stable ordering and rounding
- /api/v1/optimize response polish (advisorsRan, dataSources, actualTopK)
- Env-backed optimizer knobs added
- Normalized EXPLAIN shape
- CLI (qeo) for lint/explain/optimize without server
- Production Docker image (multi-stage, non-root, healthcheck)
- Structured request logging middleware
- CI workflow for lint/tests; release workflow for image and wheel
