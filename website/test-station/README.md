# Test Station Website

This directory contains the Docusaurus website for the Automated Analog and Neuromorphic Integrated Circuits Test-Station.

- **Public website:** https://aimlab-wustl.github.io/RCNteststation/
- **Main repository:** https://github.com/aimlab-wustl/RCNteststation

## Requirements

- Node.js 20 or later
- npm

## Local development

From `website/test-station/`, install the dependencies:

```bash
npm ci
```

Start the local development server:

```bash
npm start
```

The website will normally open at `http://localhost:3000/RCNteststation/`. Most documentation and style changes appear without restarting the server.

## Production build

```bash
npm run build
```

The generated static website is written to `build/`. The build process also checks for invalid internal links and documentation errors.

To preview the production build locally:

```bash
npm run serve
```

Do not commit `node_modules/`, `.docusaurus/`, or `build/`.

## Deployment

GitHub Actions automatically builds and deploys the website when changes under `website/test-station/` are pushed to the `main` branch.

Deployment can also be started manually:

1. Open the repository’s **Actions** tab.
2. Select **Deploy Docusaurus to GitHub Pages**.
3. Choose **Run workflow**.

The deployment workflow is defined in:

```text
.github/workflows/deploy.yml
```

## Directory structure

| Path | Contents |
| --- | --- |
| `docs/` | Documentation pages |
| `src/pages/` | Custom homepage |
| `src/css/` | Global website styling |
| `static/img/` | Images, diagrams, plots, and other static assets |
| `sidebars.js` | Documentation sidebar organization |
| `docusaurus.config.js` | Website metadata, navigation, and deployment configuration |