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

DC characterization pipelines are working end-to-end. AC and noise
measurements are currently under development. The adaptive automation
layer is planned after the AC/noise pipeline is validated.