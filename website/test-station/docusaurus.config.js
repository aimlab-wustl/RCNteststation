// @ts-check
import {themes as prismThemes} from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Automated Analog IC Test Station',
  tagline: 'Open-source hardware and AI-assisted measurement platform for analog chip testing',
  favicon: 'img/favicon.ico',

  url: 'https://aimlab-wustl.github.io',
  baseUrl: '/RCNteststation/',

  organizationName: 'aimlab-wustl',
  projectName: 'RCNteststation',

  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          editUrl: 'https://github.com/aimlab-wustl/RCNteststation/tree/main/website/test-station/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  markdown: {
    format: 'detect',
    mermaid: false,
    mdx1Compat: {
      comments: true,
      admonitions: true,
      headingIds: true,
    },
  },

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: 'img/docusaurus-social-card.jpg',
      colorMode: {
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: 'Test Station',
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'mainSidebar',
            position: 'left',
            label: 'Docs',
          },
          {
            type: 'docSidebar',
            sidebarId: 'pcbSidebar',
            position: 'left',
            label: 'PCB Design',
          },
          {
            href: 'https://github.com/aimlab-wustl/RCNteststation',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              {
                label: 'Introduction',
                to: '/docs/intro',
              },
              {
                label: 'Getting Started',
                to: '/docs/getting-started/hardware-setup',
              },
              {
                label: 'Subsystems',
                to: '/docs/subsystems/subsystems-overview',
              },
              {
                label: 'Measurements',
                to: '/docs/measurements/measurements-overview',
              },
            ],
          },
          {
            title: 'Hardware',
            items: [
              {
                label: 'PCB Overview',
                to: '/docs/pcb-design/pcb-overview',
              },
              {
                label: 'Download Files',
                to: '/docs/pcb-design/pcb-files',
              },
            ],
          },
          {
            title: 'Resources',
            items: [
              {
                label: 'GitHub Repository',
                href: 'https://github.com/aimlab-wustl/RCNteststation',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Automated Analog IC Test Station.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['c', 'python', 'bash', 'json'],
      },
    }),
};

export default config;