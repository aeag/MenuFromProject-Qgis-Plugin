# How does it work?

```{mermaid}
---
title: "How Layers Menu From Project behaves during QGIS launch"
---
flowchart TD
    A@{ shape: circle, label: "QGIS starts" } -->|splash screen displayed| B(load GUI and plugins)

    subgraph "QGIS UI main thread"
    B -->|GUI is initialized| C@{ shape: curv-trap, label: "QGIS main UI displayed" }
    C ==> Q((("QGIS is mainly usable")))
    end

    subgraph "LMFP thread (QgsTask)"
    C -.->|threaded LMFP| D[[read projects configuration]]
    D -.-> E[[check project's cache]]
    E -.->|cache still valid| F(create menus from caches JSON files)
    F == menus appear in the main UI ==> Q
    E -.->|cache has expired or is invalid| G(download/copy remote files)
    G -.->|store cache|H("{path_to_qgis_profile}/cache/menu_from_project")
    H --> F
    end
```
