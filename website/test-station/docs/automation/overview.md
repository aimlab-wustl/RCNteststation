---
id: automation-overview
title: Automation & AI
sidebar_position: 1
---

# Automation & AI

## Vision

The long-term goal is a fully automated characterization pipeline where a user can describe a chip (or paste a datasheet) and the system configures the test sequence, runs measurements, and flags anomalies — without manual intervention.

## Planned Capabilities

- **NLP-driven test configuration** — parse datasheet specs to auto-configure bias points and measurement ranges
- **GP-based adaptive sweep** — use Gaussian Process regression to intelligently choose the next bias point rather than brute-force sweeping
- **Anomaly detection** — flag measurement outliers using CUSUM or Isolation Forest
- **ML-ready output** — all measurements export structured JSON/CSV for downstream ML pipelines

## Current Status

Manual Python-driven measurements are working end-to-end for DC characterization. Automation layer is planned for after the full AC measurement pipeline is complete.
