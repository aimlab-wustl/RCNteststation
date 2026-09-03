---
id: pcb-files
title: Design Files
sidebar_position: 3
---

# PCB Design Files

## Available Files

The repository contains the editable Altium Designer source files and the
V3 fabrication packages for both boards.

| Resource | Location | Description |
|----------|----------|-------------|
| V3 Altium project | [`pcb/altium/AIMLAB_TESTSTATION_V3`](https://github.com/aimlab-wustl/RCNteststation/tree/main/pcb/altium/AIMLAB_TESTSTATION_V3) | Motherboard and daughterboard schematics, PCB layouts, project files, and output jobs |
| Motherboard V3 Gerbers | [`MotherBoardGerberV3.zip`](https://github.com/aimlab-wustl/RCNteststation/blob/main/pcb/fabrication/MotherBoardGerberV3.zip) | Motherboard Gerber and drill files |
| Daughterboard V3 Gerbers | [`DaughterBoardGerberV3.zip`](https://github.com/aimlab-wustl/RCNteststation/blob/main/pcb/fabrication/DaughterBoardGerberV3.zip) | Daughterboard Gerber and drill files |

## Repository Structure

```text
pcb/
├── altium/
│   └── AIMLAB_TESTSTATION_V3/
│       ├── Altium project files
│       ├── Motherboard schematic and PCB layout
│       ├── Daughterboard schematic and PCB layout
│       ├── Job-Mother.OutJob
│       └── Job-Daughter.OutJob
└── fabrication/
    ├── MotherBoardGerberV3.zip
    └── DaughterBoardGerberV3.zip
```