/*
 * Project: Automated Analog and Neuromorphic Integrated Circuits Test Station
 * Author: Kaiyuan (Sam) Kang
 *
 * Licensing Terms: This program is licensed under the Creative Commons
 * Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
 * You are free to share and adapt this program for noncommercial purposes,
 * provided that appropriate credit is given, a link to the license is provided,
 * and any modifications are indicated. Commercial use requires a separate
 * license from the copyright holder. See the LICENSE file for the complete
 * license terms.
 *
 * NO WARRANTY: BECAUSE THE PROGRAM IS LICENSED FREE OF CHARGE, THERE IS NO
 * WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW.
 * EXCEPT WHEN OTHERWISE STATED IN WRITING, THE COPYRIGHT HOLDERS AND/OR
 * OTHER PARTIES PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY OF ANY KIND,
 * EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
 * ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU.
 * SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY
 * SERVICING, REPAIR, OR CORRECTION. IN NO EVENT, UNLESS REQUIRED BY
 * APPLICABLE LAW OR AGREED TO IN WRITING, WILL ANY COPYRIGHT HOLDER OR ANY
 * OTHER PARTY WHO MAY MODIFY AND/OR REDISTRIBUTE THE PROGRAM BE LIABLE TO
 * YOU FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL, OR
 * CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE
 * PROGRAM (INCLUDING, BUT NOT LIMITED TO, LOSS OF DATA, DATA BEING
 * RENDERED INACCURATE, LOSSES SUSTAINED BY YOU OR THIRD PARTIES, OR A
 * FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH
 * HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH
 * DAMAGES.
 */
import React from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import styles from './index.module.css';
import useBaseUrl from '@docusaurus/useBaseUrl';

const capabilities = [
  {
    label: 'Bias generation',
    spec: '40 ch · 16-bit · 0–5 V',
    detail: (
      <>
        5× DAC80508 daisy chain
        <br />
        Per-channel RC filters on DAC4/5
      </>
    ),
  },
  {
    label: 'Voltage measurement',
    spec: '8 ch diff · 24-bit',
    detail: (
      <>
        2× ADS131A04, SPI2 DMA
        <br />
        Live stream to PC at 62.5 kSPS
      </>
    ),
  },
  {
    label: 'Current measurement',
    spec: '2 circuits · 2 kΩ–2 MΩ',
    detail: (
      <>
        OPA3S328 TIA, switchable gain
        <br />
        Calibrated against Keithley 2450
      </>
    ),
  },
  {
    label: 'Transient capture',
    spec: 'Up to 3.2 MSPS · 8,000 samples',
    detail: (
      <>
        STM32 internal ADC, TIM1/DMA burst
        <br />
        Binary USB transfer
      </>
    ),
  },
  {
    label: 'Digital I/O',
    spec: '22 lines · 16 translated',
    detail: (
      <>
        16 lines selectable at 1.8 / 3.3 / 5 V
        <br />
        6 direct STM32 lines at 3.3 V
      </>
    ),
  },
  {
    label: 'Trigger & timing',
    spec: '10 MHz tested · PFI0–15',
    detail: (
      <>
        80 MHz internal counter timebase
        <br />
        Synchronized AI acquisition
      </>
    ),
  },
];

const measurements = [
  { name: 'MOSFET', items: ['Transfer curve (Id–Vgs)', 'Output characteristics (Id–Vds)', 'Threshold voltage Vth', 'Transconductance gm', 'Body diode Vf'], status: 'done' },
  { name: 'Op-amp DC', items: ['Gain & linearity (INL)', 'Offset voltage Vos', 'Output swing', 'CMR', 'DC PSRR', 'Input bias current Ib'], status: 'done' },
  { name: 'Transient', items: ['Step response', 'Slew rate', 'Overshoot & settling'], status: 'done' },
  { name: 'AC / noise', items: ['Bode plot (gain + phase)', 'Input-referred noise PSD', 'AC PSRR & CMRR'], status: 'In progress' },
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
              Automated Analog<br />IC Test Station
            </h1>
            <p className={styles.heroSub}>
              An automated precision measurement platform for post-tapeout
              characterization of analog ICs—including MOSFETs, op-amps, and beyond.
              Generate complete sweeps, structured datasets, and publication-ready
              plots through a unified Python interface.
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
                      {m.status === 'done' ? 'Implemented' : 'In progress'}
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
              <p className={styles.pathSub}>16 AI · 2 AO · 8 DIO · 16 PFI</p>
              <p className={styles.pathDesc}>
                400 kS/s hardware-timed analog acquisition
                <br />
                GPIO-based control of the DAC chain
                <br />
                10 MHz counter output tested on PFI
              </p>
            </div>

            <div className={styles.pathDivider}>
              <span>selectable by jumper</span>
            </div>

            <div className={styles.pathCard}>
              <p className={styles.pathName}>STM32H743</p>
              <p className={styles.pathSub}>480 MHz · USB CDC · SPI2 DMA</p>
              <p className={styles.pathDesc}>
                GPIO-based control of the DAC chain
                <br />
                ADS131A04 acquisition using SPI2 DMA
                <br />
                Internal ADC capture up to 3.2 MSPS
              </p>
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