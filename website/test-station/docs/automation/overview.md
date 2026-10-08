---
id: automation-overview
title: Automation & AI
sidebar_position: 1
---

# Automation & AI

## Vision

The long-term goal is a fully automated characterization pipeline where a user can describe a chip or provide a datasheet, and the system configures the test sequence, runs measurements, analyzes the results, and flags anomalies with minimal manual intervention.

## Implemented Capabilities

- **[Adaptive AC analysis](./adaptive-ac.md)** — uses Gaussian-process-based Bayesian optimization with Ax to intelligently select frequency points and estimate gain, phase, and -3 dB bandwidth with fewer physical measurements
- **Structured data output** — measurement results, convergence history, and analysis outputs are exported in reusable CSV formats

## Planned Capabilities

- **NLP-driven test configuration** — parse datasheet specifications to automatically configure bias points and measurement ranges
- **Expanded adaptive testing** — extend adaptive measurement selection to DC, PSRR, and other characterization routines
- **Anomaly detection** — flag measurement outliers using methods such as CUSUM or Isolation Forest
- **ML-ready integration** — organize measurement outputs for broader downstream machine-learning workflows

## Current Status

DC characterization pipelines are working end-to-end. The adaptive AC-analysis pipeline has also been implemented and experimentally demonstrated. Noise measurements, adaptive PSRR testing, and the broader automated test-planning layer remain under development.