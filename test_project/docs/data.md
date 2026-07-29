# Seed Data Specification

- Deterministic generator with SEED = 20260726.
- Base date: 2026-04-01T00:00:00Z.
- 12 metric types: TEMP, HUMID, PRESS, WIND, RAIN, DUST, CO2, NOISE, LUX, VOLT, AMP, FLOW.
- Pure JDBC batch seeding with `autoCommit=false`.
