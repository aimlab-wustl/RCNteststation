---
id: pcb-files
title: Design Files
sidebar_position: 3
---

# Design Files

## Downloads

:::note
Files will be available here once the V3 design is finalised. 
:::

| File | Format | Description |
|------|--------|-------------|
| AIMLAB_V3.zip | Altium Designer | Full schematic + PCB layout project |
| AIMLAB_V3_Gerbers.zip | Gerber / Excellon | Fabrication files (JLCPCB ready) |
| AIMLAB_V3_BOM.xlsx | Excel | Bill of materials with Mouser/DigiKey part numbers |
| AIMLAB_V3_Schematic.pdf | PDF | Schematic for reference (no Altium needed) |

*Download buttons — to be added once files are uploaded to the repo*

## Design Notes

- Designed in **Altium Designer**
- Fabricated at **JLCPCB** (4-layer, 1.6mm FR4)
- All Gerbers are pre-panelised and tested
- BOM includes approved alternates for all critical components

## Repository

The full design files are hosted in the GitHub repository under `/hardware/`:

```
Automated-Analog-IC-Test-Station/
└── hardware/
    ├── altium/          ← Altium project files
    ├── gerbers/         ← Fabrication files
    ├── bom/             ← Bill of materials
    └── schematic.pdf    ← PDF schematic
```

[View on GitHub →](https://github.com/kaiyuank/Automated-Analog-IC-Test-Station/tree/main/hardware)
