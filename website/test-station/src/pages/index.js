import React from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import styles from './index.module.css';
import useBaseUrl from '@docusaurus/useBaseUrl';

const capabilities = [
  {
    label: 'Bias generation',
    spec: '40 ch · 16-bit · 0–5 V',
    detail: '5× DAC80508 daisy chain, per-channel RC filters on DAC4/5',
  },
  {
    label: 'Voltage measurement',
    spec: '8 ch diff · 24-bit',
    detail: '2× ADS131A04, SPI2 DMA, live stream to PC at 62.5 kSPS',
  },
  {
    label: 'Current measurement',
    spec: '2 circuits · 2 kΩ – 2 MΩ',
    detail: 'OPA3S328 TIA, switchable gain, calibrated against Keithley 2450',
  },
  {
    label: 'Transient capture',
    spec: 'up to 3.2 MSPS · 8000 samples',
    detail: 'STM32 internal ADC, TIM1/DMA burst, binary USB transfer',
  },
  {
    label: 'Digital I/O',
    spec: '32 lines · 1.8 / 3.3 / 5 V',
    detail: 'NI USB-6212 + STM32 GPIO, SN74LVC8T245 level translation',
  },
  {
    label: 'Trigger & timing',
    spec: 'PFI0–15 · 80 MHz counter',
    detail: 'Hardware counter output to 10 MHz, synchronized AI acquisition',
  },
];

const measurements = [
  { name: 'MOSFET', items: ['Transfer curve (Id–Vgs)', 'Output characteristics (Id–Vds)', 'Threshold voltage Vth', 'Transconductance gm', 'Body diode Vf'], status: 'done' },
  { name: 'Op-amp DC', items: ['Gain & linearity (INL)', 'Offset voltage Vos', 'Output swing', 'CMR', 'DC PSRR', 'Input bias current Ib'], status: 'done' },
  { name: 'Transient', items: ['Step response', 'Slew rate', 'Overshoot & settling'], status: 'done' },
  { name: 'AC / noise', items: ['Bode plot (gain + phase)', 'Input-referred noise PSD', 'AC PSRR & CMRR'], status: 'planned' },
];

export default function Home() {
  const frontPhoto = useBaseUrl('/img/teststation_front.jpg');
  const backPhoto = useBaseUrl('/img/teststation_back.jpg');
  return (
    <Layout title="Home" description="Automated analog IC test station">
      <main className={styles.main}>

        {/* ── Hero ── */}
        <section className={styles.hero}>
          <div className={styles.heroInner}>
            <p className={styles.eyebrow}>AIMLAB · WashU</p>
            <h1 className={styles.heroTitle}>
              Automated analog<br />IC test station
            </h1>
            <p className={styles.heroSub}>
              A Python-controlled precision measurement platform for characterizing
              tape-out ICs — MOSFETs, op-amps, and beyond. Full sweeps, structured
              data, and publication-ready plots with no manual intervention.
            </p>
            <div className={styles.heroCtas}>
              <Link className={styles.ctaPrimary} to="/docs/intro">
                Read the docs
              </Link>
              <Link className={styles.ctaSecondary} to="/docs/getting-started/hardware-setup">
                Get started
              </Link>
              <a className={styles.ctaSecondary} href="https://github.com/aimlab-wustl/RCNteststation" target="_blank" rel="noopener noreferrer">
                GitHub
              </a>
            </div>
          </div>
        </section>

        {/* ── Photos ── */}
        <section className={styles.photoSection}>
          <div className={styles.photoGrid}>
          <img
            src={frontPhoto}
            alt="Test station front view"
            className={styles.photo}
          />
          <img
            src={backPhoto}
            alt="Test station back view"
            className={styles.photo}
          />
          </div>
        </section>

        {/* ── Capabilities grid ── */}
        <section className={styles.section}>
          <div className={styles.sectionInner}>
            <h2 className={styles.sectionTitle}>Hardware capabilities</h2>
            <div className={styles.capGrid}>
              {capabilities.map((c) => (
                <div key={c.label} className={styles.capCard}>
                  <div className={styles.capTop}>
                    <span className={styles.capLabel}>{c.label}</span>
                    <span className={styles.capSpec}>{c.spec}</span>
                  </div>
                  <p className={styles.capDetail}>{c.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Measurements ── */}
        <section className={styles.section}>
          <div className={styles.sectionInner}>
            <h2 className={styles.sectionTitle}>Measurement pipelines</h2>
            <div className={styles.measGrid}>
              {measurements.map((m) => (
                <div key={m.name} className={styles.measCard}>
                  <div className={styles.measHeader}>
                    <span className={styles.measName}>{m.name}</span>
                    <span className={m.status === 'done' ? styles.badgeDone : styles.badgePlanned}>
                      {m.status === 'done' ? 'Implemented' : 'Planned'}
                    </span>
                  </div>
                  <ul className={styles.measList}>
                    {m.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Control paths ── */}
        <section className={styles.section}>
          <div className={styles.sectionInner}>
            <h2 className={styles.sectionTitle}>Two control paths, one hardware platform</h2>
            <div className={styles.pathGrid}>
              <div className={styles.pathCard}>
                <p className={styles.pathName}>NI USB-6212</p>
                <p className={styles.pathSub}>16 AI · 2 AO · 32 DIO · 16 PFI</p>
                <p className={styles.pathDesc}>400 kS/s analog input with hardware-clocked acquisition. AI0–3 buffered with OPA4388. PFI counter output to 10 MHz. Software-timed DIO at ~1 kHz.</p>
              </div>
              <div className={styles.pathDivider}>
                <span>selectable by jumper</span>
              </div>
              <div className={styles.pathCard}>
                <p className={styles.pathName}>STM32H743</p>
                <p className={styles.pathSub}>480 MHz · USB CDC · SPI2 DMA</p>
                <p className={styles.pathDesc}>Drives DAC, reads ADS131A04 with DMA, controls TIA gain. Internal ADC burst capture to 3.2 MSPS for transient measurements. Python control over USB CDC.</p>
              </div>
            </div>
          </div>
        </section>

        {/* ── Footer CTA ── */}
        <section className={styles.footerCta}>
          <div className={styles.sectionInner}>
            <h2 className={styles.footerCtaTitle}>Ready to characterize your chip?</h2>
            <div className={styles.heroCtas}>
              <Link className={styles.ctaPrimary} to="/docs/getting-started/hardware-setup">
                Hardware setup
              </Link>
              <Link className={styles.ctaSecondary} to="/docs/measurements/measurements-overview">
                View measurements
              </Link>
            </div>
          </div>
        </section>

      </main>
    </Layout>
  );
}