# Kenya Lakes Monitor

Tracking how Kenya's lakes have shrunk and grown since 1984, using satellite imagery and a water-segmentation model (U-Net).

> **Status:** In progress: project setup (Week 1)

## Why this project

Many of Kenya's Rift Valley lakes (Baringo, Nakuru, Naivasha and others) have risen sharply since 2010, flooding homes, schools and roads. Others, such as Lake Ol' Bolossat, are shrinking. We measure each lake's open-water area over time and rank the lakes by how much they have changed, in either direction.

## What we're building

1. **Baseline area history (1984–2025)** for 9 Kenyan lakes, from Digital Earth Africa's Water Observations from Space (WOfS).
2. **A water-segmentation model (U-Net)** that maps water in Sentinel-2 satellite images, evaluated on lakes it never saw during training.
3. **A vulnerability ranking** of the lakes, checked against satellite water-level data.
4. **A web map** to explore the results.

## Study lakes

Baringo · Bogoria · Nakuru · Elementaita · Naivasha · Solai · Turkana · Ol Bolossat · Magadi

## Repository layout

```
kenya-lakes-monitor/
├── data/
│   ├── lakes/        # lake outlines (lakes.geojson)
│   ├── raw/          # downloaded satellite data (not in git; on shared Drive)
│   ├── processed/    # small cleaned tables (CSV)
│   └── chips/        # model training tiles (not in git; on shared Drive)
├── src/
│   ├── baseline/     # yearly lake areas from WOfS / JRC
│   ├── dataset/      # Sentinel-2 export, labels, tiling, cleaning
│   ├── model/        # U-Net training, evaluation, inference
│   └── analysis/     # validation, ranking, charts
├── notebooks/        # exploration only; final code lives in src/
├── app/              # web map / dashboard
├── outputs/          # figures, predictions, results
├── report/           # written report and slides
└── docs/             # project plan, meeting notes, decisions
```

## Getting started

Requires **Python 3.11** and **Git**.

```bash
git clone https://github.com/Giftmasil/kenya-lakes-monitor.git
cd kenya-lakes-monitor

python -m venv .venv
# Windows:    .venv\Scripts\activate
# Mac/Linux:  source .venv/bin/activate

pip install -r requirements.txt        # everyone
pip install -r requirements-ml.txt     # only if you train or run the model - colab has it so if using colab this is not needed
```

**Google Earth Engine:** run `earthengine authenticate` once, and use the team's shared Cloud project (ask the project lead for the project ID).

**Large data** (raw satellite files, training chips, model weights) is not stored in git. It lives in the team's shared Google Drive folder. The scripts in `src/` download or regenerate it.

## How to run

_Filled in as each stage is built._

| Stage | Command | Owner | Status |
|---|---|---|---|
| Baseline lake areas | `python -m src.baseline.wofs_areas` | Aneselmus | Not started |
| Training dataset | `python -m src.dataset.build` | Melissa | Not started |
| Model training | `python -m src.model.train` | Violet | Not started |
| Validation & ranking | `python -m src.analysis.rank` | Juliet | Not started |

## Team

| Name | Role |
|---|---|
| Masila Muuo Gift | Project lead & integration |
| Aneselmus Oyando | Baseline data pipeline |
| Angwenyi Melissa | Training dataset |
| Onyango Violet Atieno | Model training & evaluation |
| Otieno Juliet Jaoko | Validation, analysis & visualisation |

## Data sources

- [Digital Earth Africa: Water Observations from Space](https://www.digitalearthafrica.org/)
- [JRC Global Surface Water](https://global-surface-water.appspot.com/) (EC JRC / Google)
- [Sentinel-2](https://dataspace.copernicus.eu/) (Copernicus) and Cloud Score+ via Google Earth Engine
- [HydroLAKES](https://www.hydrosheds.org/products/hydrolakes) (lake outlines)
- [DAHITI](https://dahiti.dgfi.tum.de/) (satellite water levels)

Each data source has its own terms of use and citation requirements; see `docs/project-plan.md`.

## License

Code is released under the MIT License (see `LICENSE`).