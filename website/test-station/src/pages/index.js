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
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './index.module.css';

const highlights = [
  {value: '40', label: 'programmable DAC outputs', detail: '16-bit · 0–5 V'},
  {value: '8', label: 'differential ADC inputs', detail: '24-bit · two ADS131A04s'},
  {value: '2', label: 'current measurement paths', detail: 'switchable TIA feedback'},
  {value: '3.2', label: 'MSPS transient capture', detail: 'STM32 internal ADC'},
];

const layers = [
  {
    number: '01', title: 'Board',
    text: 'A V3 motherboard connects programmable bias, voltage and current measurement, digital I/O, and a swappable DUT adapter.',
    link: '/docs/pcb-design/pcb-overview', linkText: 'Explore the hardware',
  },
  {
    number: '02', title: 'Firmware',
    text: 'The STM32 coordinates DAC control, precision ADC acquisition, and fast transient capture over USB CDC.',
    link: '/docs/subsystems/stm32/', linkText: 'Explore the STM32',
  },
  {
    number: '03', title: 'Python',
    text: 'Python drivers and test scripts set conditions, acquire data, and save repeatable measurements and plots.',
    link: '/docs/getting-started/software-setup', linkText: 'Explore the software',
  },
];

const results = [
  {
    type: 'DAC characterization', title: 'Programmable bias, measured',
    text: 'Static accuracy, reference selection, control paths, and output filter noise across the DAC80508 chain.',
    link: '/docs/subsystems/dac/characterization',
  },
  {
    type: 'ADC characterization', title: 'Precision acquisition, measured',
    text: 'Noise and sampling-rate tradeoffs, input filtering, and buffered versus unbuffered ADC inputs.',
    link: '/docs/subsystems/adc/characterization',
  },
];

const experiments = [
  {name: 'MOSFET', detail: 'Transfer and output curves, threshold voltage, transconductance, and body diode.', link: '/docs/measurements/mosfet/mosfet-overview'},
  {name: 'Op-amp', detail: 'DC gain, offset, common-mode range, PSRR, input bias, and step response.', link: '/docs/measurements/opamp/opamp-overview'},
];

export default function Home() {
  const backPhoto = useBaseUrl('/img/teststation_back.jpg');
  const diagram = useBaseUrl('/img/system-block-diagram.svg');

  return (
    <Layout title="Home" description="A modular board, STM32 firmware, and Python control for repeatable analog and neuromorphic IC characterization">
      <main className={styles.main}>
        <section className={styles.hero}>
          <div className={styles.heroInner}>
            <p className={styles.eyebrow}>AIMLAB · Washington University in St. Louis</p>
            <h1>Automated Analog and Neuromorphic Integrated Circuits Test-Station</h1>
            <div className={styles.heroContent}>
              <div className={styles.heroCopy}>
                <p className={styles.heroText}>
                  A modular test station for repeatable post-tapeout measurements.
                  The board, STM32 firmware, and Python software bring programmable
                  biasing, precise acquisition, and experiment control together.
                </p>
                <div className={styles.actions}>
                  <Link className={styles.primaryAction} to="/docs/intro">Explore the system</Link>
                  <Link className={styles.secondaryAction} to="/docs/measurements/measurements-overview">See measurements</Link>
                </div>
              </div>
              <figure className={styles.heroVisual}>
                <img src={backPhoto} alt="V3 test station assembled motherboard and connections" className={styles.heroPhoto} />
                <figcaption className={styles.visualCaption}>V3 motherboard · assembled board</figcaption>
              </figure>
            </div>
          </div>
        </section>

        <section className={styles.highlights} aria-label="System capabilities">
          <div className={styles.highlightGrid}>
            {highlights.map((item) => (
              <div className={styles.highlight} key={item.label}>
                <strong>{item.value}</strong>
                <span>{item.label}</span>
                <small>{item.detail}</small>
              </div>
            ))}
          </div>
        </section>

        <section className={styles.section} id="architecture">
          <div className={styles.container}>
            <div className={styles.sectionHeading}>
              <div>
                <p className={styles.kicker}>System architecture</p>
                <h2>One platform, two control paths</h2>
              </div>
              <p>
                NI USB-6212 and STM32H743 control paths connect to the same DUT interface.
                The diagram shows how bias, digital signals, precision acquisition, and
                transient capture fit together.
              </p>
            </div>
            <figure className={styles.diagramCard}>
              <div className={styles.diagramScroll}>
                <img src={diagram} alt="System block diagram showing host control, NI USB-6212 and STM32 paths, DAC bias, ADC and TIA measurement, and the DUT interface" />
              </div>
              <figcaption>
                <span>V3 motherboard and DUT adapter signal paths</span>
                <Link to="/docs/subsystems/subsystems-overview">Read the system overview →</Link>
              </figcaption>
            </figure>
          </div>
        </section>

        <section className={styles.sectionAlt}>
          <div className={styles.container}>
            <div className={styles.sectionHeadingCompact}>
              <p className={styles.kicker}>How it comes together</p>
              <h2>Built around the board, firmware, and Python</h2>
            </div>
            <div className={styles.layerGrid}>
              {layers.map((item) => (
                <article className={styles.layerCard} key={item.title}>
                  <span className={styles.layerNumber}>{item.number}</span>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                  <Link to={item.link}>{item.linkText} →</Link>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.container}>
            <div className={styles.sectionHeading}>
              <div>
                <p className={styles.kicker}>Measured performance</p>
                <h2>Explore the DAC and ADC results</h2>
              </div>
              <p>Board-level characterization documents the conditions, results, and limitations behind the headline specifications.</p>
            </div>
            <div className={styles.resultGrid}>
              {results.map((item) => (
                <Link className={styles.resultCard} to={item.link} key={item.type}>
                  <span className={styles.resultType}>{item.type}</span>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                  <span className={styles.cardArrow}>Read the results →</span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.sectionAlt}>
          <div className={styles.container}>
            <div className={styles.sectionHeading}>
              <div>
                <p className={styles.kicker}>Experiment workflows</p>
                <h2>From device connection to measurement</h2>
              </div>
              <p>Implemented MOSFET and op-amp routines use the same hardware and Python control stack. AC and noise workflows are in development.</p>
            </div>
            <div className={styles.experimentGrid}>
              {experiments.map((item) => (
                <Link className={styles.experimentCard} to={item.link} key={item.name}>
                  <h3>{item.name}</h3>
                  <p>{item.detail}</p>
                  <span>View measurements →</span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.closing}>
          <div className={styles.container}>
            <h2>Start with the system</h2>
            <p>See the hardware connections and software setup, then explore each subsystem and its measured performance.</p>
            <div className={styles.actions}>
              <Link className={styles.primaryAction} to="/docs/getting-started/hardware-setup">Hardware setup</Link>
              <a className={styles.secondaryAction} href="https://github.com/aimlab-wustl/RCNteststation">View source on GitHub</a>
            </div>
          </div>
        </section>

        <section className={styles.projectCredits} aria-labelledby="project-credits-title">
          <div className={styles.container}>
            <h2 id="project-credits-title">Project credits</h2>
            <p>Developed by Kaiyuan (Sam) Kang at AIMLAB, Washington University in St. Louis.</p>
            <p>Supported in part by a National Science Foundation Research Coordination Network grant (NSF 2332166).</p>
            <p>Original project materials are licensed under <a href="https://github.com/aimlab-wustl/RCNteststation/blob/main/LICENSE">CC BY-NC 4.0</a>.</p>
          </div>
        </section>
      </main>
    </Layout>
  );
}
