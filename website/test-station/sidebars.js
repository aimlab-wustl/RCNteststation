// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {

  // ── Main docs sidebar ──────────────────────────────────────────────────────
  mainSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/hardware-setup',
        'getting-started/software-setup',
      ],
    },
    {
      type: 'category',
      label: 'Subsystems',
      collapsed: false,
      items: [
        'subsystems/subsystems-overview',
        'subsystems/power/power',
        {
          type: 'category',
          label: 'NI DAQ',
          items: [
            'subsystems/ni-daq/ni-daq',
            'subsystems/ni-daq/ni-daq-analog-input',
            'subsystems/ni-daq/ni-daq-analog-output',
            'subsystems/ni-daq/ni-daq-digital-io',
            'subsystems/ni-daq/ni-daq-pfi',
          ],
        },
        {
          type: 'category',
          label: 'STM32',
          items: [
            'subsystems/stm32/stm32',
            'subsystems/stm32/stm32-digital-io',
            'subsystems/stm32/stm32-internal-adc',
            'subsystems/stm32/stm32-usb-cdc',
          ],
        },
        'subsystems/dac/dac',
        'subsystems/adc/adc',
        'subsystems/tia/tia',
      ],
    },
    {
      type: 'category',
      label: 'Measurements',
      collapsed: false,
      items: [
        'measurements/measurements-overview',
        {
          type: 'category',
          label: 'MOSFET',
          items: ['measurements/mosfet/mosfet-overview'],
        },
        {
          type: 'category',
          label: 'Op-Amp',
          items: ['measurements/opamp/opamp-overview'],
        },
      ],
    },
    {
      type: 'category',
      label: 'Automation & AI',
      items: ['automation/automation-overview'],
    },
  ],

  // ── PCB Design sidebar ─────────────────────────────────────────────────────
  pcbSidebar: [
    {
      type: 'category',
      label: 'PCB Design',
      collapsed: false,
      items: [
        'pcb-design/pcb-overview',
        'pcb-design/pcb-files',
      ],
    },
  ],

};

module.exports = sidebars;