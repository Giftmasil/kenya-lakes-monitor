# Kenya Lakes Monitor

Tracking how Kenya's lakes have shrunk and grown since 1984, using satellite imagery and a water-segmentation model (U-Net).

> **Status:** Week 1. Repo setup and lake outlines done; baseline lake areas and training data next.

## Why this project

Many of Kenya's Rift Valley lakes (Baringo, Nakuru, Naivasha and others) have risen sharply since 2010, flooding homes, schools and roads. Others, such as Lake Ol' Bolossat, are shrinking. We measure each lake's open-water area over time and rank the lakes by how much they have changed, in either direction.

## What we're building

1. **Baseline area history (1984–2025)** for 9 Kenyan lakes, from Digital Earth Africa's Water Observations from Space (WOfS).
2. **A water-segmentation model (U-Net)** that maps water in Sentinel-2 satellite images, evaluated on lakes it never saw during training.
3. **A vulnerability ranking** of the lakes, checked against satellite water-level data.
4. **A web map** to explore the results.

## Study lakes

Baringo · Bogoria · Nakuru · Elementaita · Naivasha · Solai · Turkana · Ol Bolossat · Magadi

Their outlines are in [`data/lakes/lakes.geojson`](data/lakes/lakes.geojson). Each outline is the lake's HydroLAKES outline combined with the largest water extent satellites have seen since 1984, plus a 1 km margin. It's a **search area**, not the lake's size. See [`outputs/figures/lakes_aoi_check.png`](outputs/figures/lakes_aoi_check.png) for a picture of all nine.

## Repository layout

```
kenya-lakes-monitor/
├── .github/          # automatic PR checks + PR/issue templates
├── data/
│   ├── lakes/        # lake outlines (lakes.geojson), committed
│   ├── processed/    # small cleaned tables (CSV), committed
│   ├── raw/          # big downloaded files: NOT in git (see "Shared Google Drive")
│   └── chips/        # model training tiles: NOT in git (see "Shared Google Drive")
├── src/
│   ├── make_lakes.py # builds data/lakes/lakes.geojson
│   ├── baseline/     # yearly lake areas from WOfS / JRC
│   ├── dataset/      # Sentinel-2 export, labels, tiling, cleaning
│   ├── model/        # U-Net training, evaluation, inference
│   └── analysis/     # validation, ranking, charts
├── notebooks/        # exploration only; final code lives in src/
├── app/              # web map / dashboard
├── outputs/          # figures, results (small files only)
├── report/           # written report and slides
└── docs/             # project plan, setup checklist, decisions, meeting notes
```

The full plan, with who does what and the file formats everyone must follow, is in [`docs/project-plan.md`](docs/project-plan.md).

---

## Getting started on your laptop

Requires **Python 3.11** and **Git** (or GitHub Desktop).

```bash
git clone https://github.com/Giftmasil/kenya-lakes-monitor.git
cd kenya-lakes-monitor

python -m venv .venv
# Windows:    .venv\Scripts\activate
# Mac/Linux:  source .venv/bin/activate

pip install -r requirements.txt        # everyone
pip install -r requirements-ml.txt     # only if you train or run the model
```

With GitHub Desktop instead: **File → Clone repository → Giftmasil/kenya-lakes-monitor**, then open the folder in VS Code and run the `venv` and `pip` lines in its terminal.

**Google Earth Engine:** run `earthengine authenticate` once, and use the team's shared Cloud project (ask the project lead for the project ID).

---

## Working in Google Colab

Colab's free plan is enough for this project, including the GPU for model training. **You don't need Colab Pro.**

### Why you need a setup cell

Opening a notebook from GitHub in Colab gives you **only that one notebook file**, not the rest of the repo (`src/`, `data/lakes/`…). On top of that, Colab starts on a **fresh, empty machine every session**. So every notebook that uses the repo starts with a setup cell that clones it.

### Step 1: Run this setup cell first, every session

Paste it as the **first cell** of every notebook:

```python
# ── Setup: run first in every Colab session ──────────────────────────────
import os
REPO = "/content/kenya-lakes-monitor"

if not os.path.exists(REPO):                       # first run this session: download the repo
    !git clone -q https://github.com/Giftmasil/kenya-lakes-monitor.git {REPO}
%cd {REPO}
!git pull -q                                       # get the latest version of main
!pip install -q -r requirements.txt                # install what Colab doesn't already have
# !pip install -q -r requirements-ml.txt           # uncomment only for model training
```

It takes about 30–60 seconds. After that, everything in the repo works as it does on your laptop:

```python
import geopandas as gpd
lakes = gpd.read_file("data/lakes/lakes.geojson")
lakes.explore(column="type")                       # interactive map of the 9 lakes

from src.make_lakes import LAKES                   # the team's own code imports normally
```

**Testing a teammate's branch before approving their PR:** add `!git checkout <branch-name>` after the `git pull` line.

### Step 2: Connect the shared Google Drive (when you need big data)

```python
from google.colab import drive
drive.mount("/content/drive")
DATA = "/content/drive/MyDrive/kenya-lakes"        # the team's shared data folder
```

The first time, Colab asks you to allow access to your Drive. See **Shared Google Drive** below for what's in the folder and how to make it show up.

### Step 3: Open, edit and save notebooks

- **Open a notebook:** in Colab, go to **File → Open notebook → GitHub**, enter `Giftmasil/kenya-lakes-monitor`, and pick a notebook from `notebooks/`. Or use this URL pattern:
  `https://colab.research.google.com/github/Giftmasil/kenya-lakes-monitor/blob/main/notebooks/<name>.ipynb`
- **Save it back to GitHub.** `main` is protected, so Colab can't save to it directly:
  1. On github.com, use the branch dropdown to create a new branch (e.g. `notebooks/explore-lakes`).
  2. In Colab: **Edit → Clear all outputs** (maps and images can push a notebook over the 5 MB limit in our checks).
  3. **File → Save a copy in GitHub**, pick **your branch**, write a commit message, and save.
  4. On github.com, open a **pull request** from that branch.
- **Never use `git push` from inside Colab.** It needs a GitHub access token, and tokens pasted into notebooks tend to get committed by accident.

### Quick shortcut: reading a single file

If a notebook only needs one file from the repo, it can skip the setup cell and read the file straight from GitHub:

```python
lakes = gpd.read_file("https://raw.githubusercontent.com/Giftmasil/kenya-lakes-monitor/main/data/lakes/lakes.geojson")
```

### Free Colab tips

- Free sessions **disconnect after a few hours or when idle**, and everything on the Colab machine is deleted. Save anything you want to keep to **Drive**.
- When training the model, **save a checkpoint to Drive after every epoch**, so a disconnect only costs one epoch.
- Only the model training needs a GPU: **Runtime → Change runtime type → T4 GPU**. Everything else runs on the normal CPU runtime.

---

## Shared Google Drive: what goes where

**Rule:** GitHub holds the **code and small results**. Google Drive holds the **big files**. Anything big can be rebuilt by a script in `src/`, so Drive is a working store, not the only copy of anything important.

| Goes in **GitHub** | Goes on **Google Drive** |
|---|---|
| All code (`src/`, `app/`) | Raw satellite downloads (`.tif`) |
| Notebooks (with outputs cleared) | Sentinel-2 composites exported from Earth Engine |
| `data/lakes/lakes.geojson` | Training chips (thousands of small `.tif` files) |
| Small CSVs (`data/processed/`, `outputs/results/`) | Model weights (`.pth`) |
| Figures (`.png`) for the report and README | Full-lake prediction maps (`.tif`) |
| Docs, report, slides | Anything over 5 MB |

Our PR checks block `.tif`, `.pth`, `.zip` and `.env` files, and anything over 5 MB, so big files can't end up in GitHub by mistake.

### Folder layout on Drive

The project lead shares one folder, `kenya-lakes`, with the whole team as **Editor**. Inside it:

```
kenya-lakes/
├── raw/
│   ├── wofs/{lake_id}/         # WOfS water maps cropped per lake (Aneselmus)
│   └── s2/{lake_id}/           # Sentinel-2 composites from Earth Engine (Melissa)
├── chips/
│   ├── train/  val/  test/     # 256×256 training tiles + manifest.csv (Melissa)
│   └── test_hand/              # 40 hand-corrected test tiles (Melissa + Juliet)
├── models/                     # U-Net checkpoints and best weights (Violet)
├── predictions/                # full-lake water maps for 2016 and 2025 (Violet)
└── exports/                    # temporary landing spot for Earth Engine exports
```

The subfolders mirror the repo's `data/` folder, so the same file paths work whether data is on Drive or on your laptop.

### Make the shared folder appear in Colab (each member, once)

A folder someone else shared with you **doesn't** show up under `MyDrive/` in Colab until you add a shortcut:

1. Open Google Drive → **Shared with me** → right-click `kenya-lakes`.
2. Choose **Organise → Add shortcut** (older menus say **Add shortcut to Drive**) and pick **My Drive**.
3. In Colab it's now at `/content/drive/MyDrive/kenya-lakes`.

### Earth Engine exports

`Export.image.toDrive(...)` always saves into **your own** My Drive (in a folder named by the `folder=` argument), not into the shared folder. After an export finishes, **move** the files into the right place under `kenya-lakes/` (e.g. `raw/s2/naivasha/`) so the rest of the team can see them.

### Using Drive data from scripts

Scripts should take the data location as an argument rather than hard-coding a path, so the same script runs on Colab and on laptops:

```bash
python -m src.baseline.wofs_areas --data-dir /content/drive/MyDrive/kenya-lakes   # Colab
python -m src.baseline.wofs_areas --data-dir data                                 # laptop
```

---

## How to contribute

1. Create a branch (`<task-id>/<short-name>`, e.g. `A2/lake-areas`). In GitHub Desktop: **Current branch → New branch**.
2. Work in **your own folder** under `src/` and commit as you go.
3. **Publish branch → Create Pull Request**, and fill in the template.
4. A PR can merge only when:
   - **the automatic checks pass.** They block data files, files over 5 MB, broken Python and failing tests, and check that `requirements.txt` installs.
   - **one teammate has approved it.**
5. Merge with **Squash and merge**. The branch is deleted automatically.

Push at least once a week, even if the work is unfinished. New members: start with [`docs/setup.md`](docs/setup.md).

## How to run

_Filled in as each stage is built._

| Stage | Command | Owner | Status |
|---|---|---|---|
| Lake outlines | `python -m src.make_lakes --hydrolakes <path to HydroLAKES_polys_v10.shp>` | Gift | ✅ Done (output already committed; only rerun if the lake list changes) |
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