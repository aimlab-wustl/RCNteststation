import Heading from '@theme/Heading';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Programmable Test Hardware',
    icon: '🔌',
    description: (
      <>
        The platform includes DAC-based bias generation, ADC measurement,
        NI-DAQ/STM32 control, precision references, and a ZIF socket interface
        for analog and mixed-signal chip testing.
      </>
    ),
  },
  {
    title: 'Python-Based Automation',
    icon: '🐍',
    description: (
      <>
        Python scripts control the measurement flow, including setting voltages,
        triggering acquisition, saving raw data, running calibration routines,
        and organizing experiment metadata.
      </>
    ),
  },
  {
    title: 'Future AI-Driven Testing',
    icon: '🤖',
    description: (
      <>
        The long-term goal is a closed-loop test station where an AI or Bayesian
        optimization module selects the next experiment based on measured chip
        behavior.
      </>
    ),
  },
];

function Feature({title, icon, description}) {
  return (
    <div className="col col--4">
      <div className={styles.featureCard}>
        <div className={styles.featureIcon}>{icon}</div>
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}