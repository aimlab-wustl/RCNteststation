# ADC Website Image Export

This folder contains the finalized ADC figures copied from the analysis outputs
and renamed to stable filenames for use in Docusaurus MDX pages.

## Suggested MDX paths

- `../../../static/img/adc/adc_noise_vs_speed.png`
- `../../../static/img/adc/ads_osr_tradeoff.png`
- `../../../static/img/adc/ads_datasheet_comparison.png`
- `../../../static/img/adc/ads_filter_comparison.png`
- `../../../static/img/adc/ads_buffered_vs_unbuffered.png`

## Copied figures

| File | Description | Suggested page usage |
| --- | --- | --- |
| `adc_noise_vs_speed.png` | Cross-system ADC comparison showing noise versus speed for ADS131A04, NI USB-6212, STM32 ADC, and DAQ6510 reference. | characterization.mdx (optional late-section cross-system context) |
| `ads_osr_tradeoff.png` | ADS131A04 OSR tradeoff plot showing measured shorted-input noise versus output sample rate, with TI typical values overlaid. | index.mdx and characterization.mdx |
| `ads_datasheet_comparison.png` | ADS131A04 measured shorted-input noise compared with datasheet-typical values across OSR. | characterization.mdx |
| `ads_filter_comparison.png` | Comparison of the two ADS input filter families (10 nF versus 1 nF) across tested rates. | characterization.mdx |
| `ads_buffered_vs_unbuffered.png` | Comparison of buffered and unbuffered ADS front-end paths, highlighting noise and DC-error behavior. | characterization.mdx |

## Notes

- `ads_osr_tradeoff.png` should appear on both the ADC overview and detailed characterization pages.
- `ads_datasheet_comparison.png`, `ads_filter_comparison.png`, and `ads_buffered_vs_unbuffered.png` are mainly for the detailed characterization page.
- `adc_noise_vs_speed.png` is useful as a short final comparison against NI and STM32, but should not dominate the ADS-focused page.
