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