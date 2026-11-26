# Kenyan Lakes Change Monitor — Project Plan & Task Breakdown

**Project:** Identifying Kenya's most vulnerable lakes using satellite imagery and ML image segmentation
(adapted from *Let's Learn AI – StepUp*, Topic 2.1 "Image Processing Project")

**Repo:** https://github.com/Giftmasil/kenya-lakes-monitor · **Last updated:** 26 Nov 2026

**Group members**

| # | Name | Reg. No. | Role |
|---|------|----------|------|
| 1 | Masila Muuo Gift | SCS3/2109/2024 | Project Lead & Integrator |
| 2 | Aneselmus Oyando | SCS3/2127/2024 | Data Engineer (baseline lake-area pipeline) |
| 3 | Angwenyi Melissa | SCS3/149260/2024 | ML Data Engineer (training dataset) |
| 4 | Onyango Violet Atieno | SCS3/2137/2024 | ML Engineer (model training & evaluation) |
| 5 | Otieno Juliet Jaoko | SCS3/2111/2024 | Validation, Analysis & Visualisation |

> **On roles:** these are proposed assignments. Swap them in the kickoff meeting to match people's strengths. Keep the *roles* as they are, because the plan depends on each role having exactly one owner.

> **On the timeline:** the plan is written as **6 weeks** (Week 1 to Week 6). If your deadline is shorter or longer, stretch or squeeze the weeks but keep the order. The dependencies between tasks don't change.

---

## 1. What "fully done" means

The project is done only when **all** of these are true:

- [ ] A public GitHub repo where someone outside the group can clone it, follow the README, and reproduce the results.
- [ ] A **yearly open-water area time series (1984–2025)** for every lake on the study list, with unreliable years flagged rather than hidden.
- [ ] A **trained water-segmentation model** (U-Net) that finds water in Sentinel-2 images. It must be evaluated on lakes it never saw in training and compared against a simple non-ML baseline.
- [ ] Model predictions for two comparison years (e.g. **2016 vs 2025**) for every lake, with area change computed from them.
- [ ] **Validation** of the areas against an independent source (satellite water levels from DAHITI and published figures).
- [ ] A **vulnerability ranking** of the lakes: which are shrinking, which are expanding and flooding, which are stable, and how confident we are.
- [ ] A **written report**, a **slide deck**, and a **demo** (a small web map or dashboard).
- [ ] A **limitations section** that says honestly what didn't work (e.g. swampy lakes like Ol Bolossat).

---

## 2. Key project decisions (settle these in Week 1, then don't change them)

| Decision | Choice | Why |
|---|---|---|
| Study lakes | **Baringo, Bogoria, Nakuru, Elementaita, Naivasha, Solai, Turkana, Ol Bolossat, Magadi** (9 lakes) | Mix of growing (Rift lakes), shrinking (Ol Bolossat), dam-affected (Turkana) and hard cases (saline/soda lakes: Magadi, Bogoria; swamp: Ol Bolossat). Lake Victoria is out of scope: too big, cross-border, and covered in water hyacinth. Add it only as a stretch goal. |
| Question we answer | "Which lakes changed most, in **either** direction?" | In Kenya many lakes are *rising* and flooding, so shrinking is only half the story. |
| Lake outlines | **HydroLAKES outline ∪ WOfS all-time water (≥ 5% of clear looks)**, holes filled, **+1 km buffer** | HydroLAKES outlines are older than the post-2010 lake rise; WOfS adds the newly flooded area. Built by `src/make_lakes.py`. |
| Lake types | **freshwater** (Baringo, Naivasha), **saline** (Bogoria, Solai, Nakuru, Elementaita, Magadi, Turkana), **swamp** (Ol Bolossat) | Type affects how hard a lake is to map and how confident we are in its results. |
| Baseline area data | **Digital Earth Africa WOfS annual summaries** (1984–2025) | Ready-made water maps, free, no account needed. |
| Model input imagery | **Sentinel-2 L2A (harmonised)** via Google Earth Engine, 10 m | High resolution and free. |
| Model training labels | **JRC Global Surface Water monthly history** (in Earth Engine, up to 2021), plus a **small hand-corrected test set** | Free labels at scale. The hand-labelled set makes the evaluation honest. |
| Area projection | **EPSG:6933** (equal-area) | Every pixel covers the same ground area, so pixel counts convert to km² correctly. |
| Comparison season | **Dry season, January–February composite** each year | Avoids rainy-season noise and is usually less cloudy. |
| Cloud masking | **Cloud Score+**, `cs_cdf ≥ 0.60` | Current best practice in Earth Engine. |
| Model | **U-Net** (PyTorch + `segmentation-models-pytorch`) | The book's TensorFlow Object Detection API is deprecated, and bounding boxes give poor area estimates. |
| Compute | Earth Engine (Community tier, free for non-commercial use) + Google Colab GPU | No cost. |

---

## 3. Interface contracts (the most important section)

Five people work in parallel, so we **fix the formats of everything handed between people on Day 1**. Then nobody waits on anybody, and integration doesn't break at the end. Any change to a contract needs the Lead's approval and a message in the group chat.

### C1 — Lake list: `data/lakes/lakes.geojson`
*Owner: Gift. Used by everyone.*

```
Format: GeoJSON FeatureCollection, EPSG:4326 (lon/lat), one Polygon per lake (9 lakes)
Each polygon = HydroLAKES outline ∪ WOfS all-time water extent, holes filled, +1 km buffer
properties:
  lake_id             : str   e.g. "baringo"   (lowercase, no spaces; the key used everywhere)
  name                : str   e.g. "Lake Baringo"
  type                : str   "freshwater" | "saline" | "swamp"
  split               : str   "train" | "val" | "test"   (model data split, see C3)
  centre_lon          : float
  centre_lat          : float
  hylak_ids           : list[int]  HydroLAKES IDs inside the outline
  hydrolakes_area_km2 : float      total area of those HydroLAKES polygons
  wofs_max_area_km2   : float      largest water extent WOfS has seen (1984-2025)
  aoi_area_km2        : float      area of the outline itself (includes the 1 km buffer)
  country             : str        "Kenya" (Turkana: "Kenya/Ethiopia")
```
**Status: done** (`src/make_lakes.py`, check image `outputs/figures/lakes_aoi_check.png`).

**Important:** the outline is a *search area*, not the lake's area. To measure a lake in any given year, take the water inside the outline that is connected to the lake (see A2), never the outline's own area.

### C2 — Baseline areas: `data/processed/wofs_areas.csv`
*Owner: Aneselmus. Used by Juliet and Gift.*

```
lake_id, year, area_km2, pct_unobserved, median_clear_looks, reliable
baringo, 2025, 225.7, 0.1, 33, True
```
`reliable = pct_unobserved < 5 AND median_clear_looks >= 3`

### C3 — Training chips: `data/chips/{split}/{lake_id}_{year}_{row}_{col}_img.tif` and `..._lbl.tif`
*Owner: Melissa. Used by Violet.*

```
Image : GeoTIFF, 256 x 256 px, 10 m, float32, 6 bands in this order:
        B2 (blue), B3 (green), B4 (red), B8 (NIR), B11 (SWIR1), B12 (SWIR2)
        reflectance scaled to 0–1
Label : GeoTIFF, 256 x 256 px, uint8:  0 = land, 1 = water, 255 = no data/ignore
Split : by LAKE, never by chip (prevents data leakage)
        train: baringo, naivasha, turkana (south basin), elementaita
        val  : solai, bogoria
        test : nakuru, magadi, ol_bolossat
Manifest: data/chips/manifest.csv  ->  chip_id, lake_id, year, split, pct_water, pct_nodata
```

### C4 — Model predictions: `outputs/predictions/{lake_id}_{year}_water.tif`
*Owner: Violet. Used by Juliet.*

```
GeoTIFF covering the whole lake polygon from C1, 10 m, uint8: 0 = land, 1 = water, 255 = no data
Plus outputs/predictions/model_areas.csv -> lake_id, year, area_km2, pct_nodata
```

### C5 — Final results: `outputs/results/vulnerability_ranking.csv`
*Owner: Juliet. Used by Gift (report) and the dashboard.*

```
lake_id, area_2010_km2, area_2025_km2, pct_change, trend_km2_per_yr, trend_p_value,
direction ("shrinking"|"expanding"|"stable"), model_vs_wofs_diff_pct, validation_r, confidence ("high"|"medium"|"low")
```

---

## 4. Repository setup and team process

### Repo structure (Gift creates this in Week 1)

```
kenya-lakes-monitor/
├── .github/
│   ├── workflows/checks.yml  # automatic checks on every PR (must pass to merge)
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/       # task.md, bug.md
├── README.md                 # what, why, how to reproduce, results summary
├── requirements.txt          # core Python dependencies (everyone)
├── requirements-ml.txt       # extra dependencies for model training
├── data/
│   ├── lakes/lakes.geojson   # C1 (small, committed)
│   ├── raw/                  # NOT committed (gitignored), downloaded by scripts
│   ├── processed/            # small CSVs committed (C2)
│   └── chips/                # NOT committed, stored on shared Drive (C3)
├── src/
│   ├── baseline/             # Aneselmus: WOfS/JRC area pipeline
│   ├── dataset/              # Melissa: Earth Engine export, tiling, cleaning
│   ├── model/                # Violet: training, evaluation, inference
│   ├── analysis/             # Juliet: validation, ranking, charts
│   └── make_lakes.py         # Gift: builds data/lakes/lakes.geojson
├── notebooks/                # exploration only; final logic must live in src/
├── app/                      # Juliet: dashboard / web map
├── outputs/                  # figures, predictions, results (small files only)
├── report/                   # Gift: report.md + figures, slides
└── docs/                     # project-plan.md, setup.md, decisions.md, meetings.md
```

### Working rules (everyone)

1. **Work in your own folder** (`src/baseline/`, `src/dataset/`, `src/model/`, `src/analysis/`) so you rarely clash with anyone. Optional: track your tasks as issues on the project board (*Backlog → Ready → In progress → In review → Done*).
2. **Never push to `main`.** Work on a branch named `task-id/short-name` (e.g. `A3/quality-flags`) and open a Pull Request.
3. **Every PR needs one approval** (ideally from your review partner below) **and must pass the automatic checks** before it can merge. `main` is protected: direct pushes, force pushes and deleting `main` are blocked. Merges are **squash** only.
   The checks (`.github/workflows/checks.yml`) fail the PR if it adds data/model/secret files (`.tif`, `.pth`, `.zip`, `.env`…) or any file over 5 MB, if `requirements.txt` no longer installs, if Python code has syntax errors or undefined names, or if a test fails.
4. **No large data in git.** Raw files, chips and model weights go on the shared Google Drive folder. The repo holds the *scripts* that make them.
5. **Every script must run from the command line**, e.g. `python src/baseline/wofs_areas.py --lakes data/lakes/lakes.geojson --out data/processed/wofs_areas.csv`. A notebook alone doesn't count as done.
6. **Seed everything** (`random`, `numpy`, `torch`) so results can be reproduced.
7. **Write your own docs:** each person writes the README section and the report section for their own part.
8. **Push at least once a week**, even unfinished work. If it isn't on GitHub, it doesn't exist.
9. **Weekly check-in** (5 minutes in the group chat is fine): what I pushed, what's next, what's blocking me.
10. **Blocked for more than 24 hours? Say so in the group chat.** Silence is the biggest risk to the project.

### Review pairs (who reviews whose PRs)

| Author | Reviewer |
|---|---|
| Aneselmus (baseline) | Juliet (she uses his output) |
| Melissa (dataset) | Violet (she uses her output) |
| Violet (model) | Melissa |
| Juliet (analysis/app) | Aneselmus |
| Gift (repo, report) | Juliet |

---

## 5. Timeline overview

| Week | Phase | Main goal | Milestone at end of week |
|---|---|---|---|
| 1 | Setup & design | Repo, contracts, lake list, accounts, everyone running code | **M1:** repo live, `lakes.geojson` done, all accounts working |
| 2 | Data | Baseline areas + first training chips | **M2:** `wofs_areas.csv` complete; first 200+ chips exported |
| 3 | Data → Model | Full chip dataset + baseline model working | **M3:** full dataset done; threshold baseline scored |
| 4 | Model | U-Net trained and evaluated | **M4:** U-Net beats baseline on test lakes; predictions exported |
| 5 | Analysis | Validation, ranking, charts, dashboard | **M5:** `vulnerability_ranking.csv` + dashboard draft |
| 6 | Finish | Report, slides, reproducibility check, freeze | **M6:** final submission; repo tagged `v1.0` |

Dependency chain (what blocks what):

```
Gift: C1 lakes.geojson ──┬──> Aneselmus: baseline areas ──────────────┐
                         ├──> Melissa: chips ──> Violet: model ──> predictions ──┼──> Juliet: validation + ranking ──> Gift: report
                         └──> Juliet: hand-labelled test set ──────────┘
```
**`lakes.geojson` blocks everyone, so Gift delivers it by Day 3 of Week 1.** ✅ Done.

---

## 6. Task breakdown per member

Each task has: **what to do**, **output**, and **done when** (how we check it's actually finished).

---

### 6.1 Masila Muuo Gift — Project Lead & Integrator

Gift's job is to make sure the pieces fit together and the project gets submitted complete. Gift owns the repo, the lake list, the timeline, and the final report and presentation.

| ID | Task | Week |
|---|---|---|
| G1 | Repo & process setup | 1 |
| G2 | Lake list & study design (C1) | 1 |
| G3 | Accounts & access check for all members | 1 |
| G4 | Weekly coordination & decisions log | 1–6 |
| G5 | Integration checks at every milestone | 2–6 |
| G6 | Report: intro, background, method overview, editing | 4–6 |
| G7 | Slides & demo script | 6 |
| G8 | Final reproducibility test & release | 6 |

**G1 — Repo & process setup**
- Do: create the GitHub repo with the structure in §4; add `.gitignore` (data/raw, data/chips, *.tif, *.pth), `requirements.txt` + `requirements-ml.txt`, a licence (MIT) and a README skeleton. Protect `main` (require a PR + 1 review). Create the GitHub Projects board and one issue per task ID in this document. Create the shared Google Drive folder with `raw/`, `chips/` and `models/`.
- Output: repo URL, board URL, Drive link shared in the group chat.
- Done when: every member has pushed one test branch and opened one test PR (`docs/setup.md` explains how).
- **Status:** repo, folders, README, requirements, licence, templates, ruleset on `main` and PR checks are **done**. Remaining: invite all members, shared Drive folder, each member's first PR.

**G2 — Lake list & study design (C1)**
- Do: for each of the 9 lakes, combine its HydroLAKES outline with the largest water extent WOfS has ever seen, fill holes (islands), add a 1 km buffer, and add the C1 properties. Check every outline against satellite water maps by eye.
- Output: `data/lakes/lakes.geojson`, built by `python -m src.make_lakes --hydrolakes <path to HydroLAKES_polys_v10.shp>`, plus the check image `outputs/figures/lakes_aoi_check.png`.
- Done when: the file has 9 lakes with all fields filled and every outline contains its lake's largest extent.
- **Status: done.** Notes from building it:
  - Magadi is split into 8 HydroLAKES fragments (soda pan); all fragments inside its water are included.
  - River channels narrower than ~150 m are removed before deciding what counts as lake water.
  - Turkana's outline extends into Ethiopia (Omo delta) and ~25 km up the Turkwel River at ~3°N (a wide channel WOfS sees as water). It adds < 0.1% to Turkana's area, so it is left in.
  - Naivasha's outline includes Lake Oloidien (joined to Naivasha in high-water years).
- Still to do: `docs/study_design.md` (why these lakes, the research question, the definition of "vulnerable"). Optional.

**G3 — Accounts & access**
- Do: make sure every member has a GitHub account, a Google account registered for **Earth Engine (non-commercial, Community tier)** under one shared Cloud project, Colab access, and a DAHITI registration (Juliet needs this one). Each person runs a "hello world": prints the Sentinel-2 collection size for Lake Naivasha in Earth Engine.
- Output: checklist in `docs/setup.md` with a tick per person.
- Done when: all 5 have run the Earth Engine test successfully.

**G4 — Coordination**
- Do: run the weekly check-in; keep `docs/meetings.md` and `docs/decisions.md` (every decision with its date and reason). Update the board. Chase anyone blocked for more than 24 h. If someone falls more than a week behind, re-assign their work or pair someone with them.
- Done when: the notes exist for every week.

**G5 — Integration checks**
- Do: at each milestone (M2–M5), pull `main` on a clean environment and run every script in order. Check that each output matches its contract (column names, file names, band order). Log problems as issues.
- Done when: each milestone has a short pass/fail note in `docs/integration.md`.

**G6 — Report (overall editor)**
- Do: write the Introduction, Problem Statement (Kenya context: rising Rift lakes since 2010, shrinking Ol Bolossat/Kamnarok, Turkana and the Gibe III dam), Objectives, Data Sources and Method Overview sections. Collect each member's section and edit for one consistent voice. Make sure every figure has a caption and every number has a source.
- Report outline (`report/report.md`):
  1. Abstract
  2. Introduction & problem (Gift)
  3. Study area & data sources (Gift + Aneselmus)
  4. Baseline area method (Aneselmus)
  5. Training dataset & cleaning (Melissa)
  6. Model & evaluation (Violet)
  7. Validation & vulnerability ranking (Juliet)
  8. Discussion, limitations & ethics (all; Gift edits)
  9. Conclusion & future work (Gift)
  10. References
  11. Appendix: individual contributions table
- Done when: every section is complete, all figures render, and references are formatted.

**G7 — Slides & demo**
- Do: 10–12 slides: problem → data → method → model results → lake ranking → map demo → limitations → next steps. Assign each member the slides they'll present (their own part). Run one full rehearsal.
- Done when: rehearsal fits the time limit and every member has presented their part once.

**G8 — Final reproducibility test & release**
- Do: on a fresh machine or Colab, clone the repo and follow **only** the README, start to finish. Fix anything that breaks. Tag release `v1.0`.
- Done when: a member who didn't write the code (ideally Juliet or Melissa) reproduces the key result (the ranking table) from the README alone.

---

### 6.2 Aneselmus Oyando — Data Engineer (baseline lake-area pipeline)

Aneselmus produces the long-term "ground truth" area history for each lake from ready-made water maps. This is the backbone of the analysis and doesn't need ML.

| ID | Task | Week |
|---|---|---|
| A1 | WOfS download pipeline | 1–2 |
| A2 | Per-lake water extraction & area | 2 |
| A3 | Data quality flags & cleaning | 2 |
| A4 | JRC cross-check | 3 |
| A5 | Baseline charts & docs | 3 |
| A6 | Support Juliet with validation data | 4–5 |

**A1 — WOfS download pipeline**
- Do: write `src/baseline/fetch_wofs.py`. For each lake in `lakes.geojson`, search the Digital Earth Africa STAC API (`https://explorer.digitalearth.africa/stac/search`, collection `wofs_ls_summary_annual`) by the lake's bounding box, and read the `frequency` and `count_clear` layers for every available year, cropped to the lake polygon. Handle lakes that span more than one tile (merge them).
- Note: a prototype script (`lake_area.py`) already exists from early exploration. Use it as a **reference only**: rewrite it into clean, tested, documented functions you understand fully, because you'll have to explain every line.
- Output: cropped rasters on Drive under `raw/wofs/{lake_id}/`.
- Done when: all 9 lakes have files for every available year (1984–2025, with known gaps).

**A2 — Per-lake water extraction & area**
- Do: a pixel is **water** in a year if `frequency ≥ 0.5` (wet in at least half of that year's clear looks). Keep only water **inside the lake polygon** and **connected** to the main lake body (use `scipy.ndimage.label`). Area = water pixel count × 900 m² (30 m pixels in EPSG:6933), converted to km².
- Output: `src/baseline/wofs_areas.py` producing `data/processed/wofs_areas.csv` (contract C2).
- Done when: the CSV has every lake × year and Baringo's numbers are close to the published ones (≈118 km² in 1995, ≈190 km² in 2014).

**A3 — Data quality flags & cleaning**
- Do: for each lake-year compute `pct_unobserved` (% of the lake footprint with zero clear looks) and `median_clear_looks`. Mark `reliable = False` if `pct_unobserved ≥ 5` or `median_clear_looks < 3`. **Never write 0 km² for a missing year**: an empty map is missing data, not a dried-up lake. Document known gaps (1988–93 and 1996–98 are mostly empty over Kenya).
- Output: the flag columns in C2 + `docs/data_quality.md`.
- Done when: no unreliable year shows up as a "real" value anywhere downstream.

**A4 — JRC cross-check**
- Do: in Earth Engine, compute yearly areas from **JRC Global Surface Water** (`JRC/GSW1_4/YearlyHistory`, classes "seasonal" + "permanent") for the same lakes, 1984–2021. Compare with the WOfS areas: correlation and mean % difference per lake.
- Output: `data/processed/jrc_areas.csv` + a comparison table in the report.
- Done when: the comparison is written up, with an explanation for any lake where the two sources differ by more than 10%.

**A5 — Baseline charts & docs**
- Do: one line chart per lake (area vs year, unreliable years shown as hollow points), plus one combined chart. Write report section 4 and the README "Baseline data" section.
- Done when: the charts are in `outputs/figures/baseline/` and both sections are merged.

**A6 — Support validation**
- Do: help Juliet join the area series with DAHITI water levels (matching years and lake IDs).

---

### 6.3 Angwenyi Melissa — ML Data Engineer (training dataset)

Melissa builds the dataset the model learns from: satellite images cut into tiles ("chips") with matching water/land labels, cleaned and split correctly. Errors here quietly ruin the model, so this role is about care and checking.

| ID | Task | Week |
|---|---|---|
| M1 | Sentinel-2 cloud-free composites | 1–2 |
| M2 | Label generation from JRC | 2 |
| M3 | Tiling into aligned chips | 2–3 |
| M4 | Dataset cleaning & manifest | 3 |
| M5 | Hand-corrected test set (with Juliet) | 3 |
| M6 | Inference composites for 2016 & 2025 | 3 |
| M7 | Dataset documentation | 3–4 |

**M1 — Sentinel-2 composites**
- Do: in Earth Engine (Python API in Colab), for each lake and each year 2017–2021 (training years), build a **January–February median composite** from `COPERNICUS/S2_SR_HARMONIZED`. Mask clouds using Cloud Score+ (`GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`, band `cs_cdf`, keep pixels ≥ 0.60). Select bands B2, B3, B4, B8, B11, B12, resample the 20 m bands to 10 m, and scale reflectance to 0–1.
- Output: `src/dataset/s2_composites.py`; exports to Drive.
- Done when: a true-colour preview of each composite shows no obvious cloud, saved in `outputs/figures/composites/`.

**M2 — Labels from JRC**
- Do: for the same lake-years, make a water mask from `JRC/GSW1_4/MonthlyHistory` for January–February (water = 2, land = 1, no data = 0). Combine the two months: water if water in either month with an observation, land if observed and never water, otherwise 255 (ignore). Resample to 10 m with **nearest-neighbour** (never bilinear, since labels are categories).
- Output: `src/dataset/jrc_labels.py`.
- Done when: the labels line up with the shoreline in the composite (check 5 lakes visually by overlaying them).

**M3 — Tiling into aligned chips**
- Do: cut the image and label into **256 × 256 px** chips on **one fixed grid per lake** (the same grid for every year), so the same chip ID always covers the same ground. Use 32 px overlap for training chips. Name files per contract C3.
- Done when: random spot-checks of 20 chips show the image and label line up exactly, and the same chip ID covers identical bounds in two different years.

**M4 — Dataset cleaning & manifest**
- Do: drop chips with more than 30% no-data. Cap all-land chips so they're at most 30% of the training set (otherwise the model learns "always say land"). Flag chips that might contain **salt crust** (Magadi, Bogoria shores) or **floating vegetation** for the report. Write `manifest.csv` with water %, no-data % and split. **Split by lake** per contract C3: a lake's chips must never appear in two splits.
- Output: `data/chips/` on Drive + `manifest.csv` in the repo.
- Done when: a script `src/dataset/check_dataset.py` passes. It checks shapes, band count, label values ∈ {0, 1, 255}, no lake in two splits, and prints class balance per split.

**M5 — Hand-corrected test set (with Juliet)**
- Do: pick about **40 test chips** (from Nakuru, Magadi and Ol Bolossat; mix of easy and hard). Fix their labels by hand in QGIS (or Label Studio) wherever JRC is wrong: hyacinth, salt, swamp edges, new flooded areas after 2021. Split the work 20/20 with Juliet, then each checks the other's half.
- Output: `data/chips/test_hand/` + notes on which errors were found.
- Done when: all 40 are corrected and cross-checked. **This set is the most important evaluation in the project.**

**M6 — Inference composites**
- Do: same as M1 but for the **two comparison years, 2016 and 2025**, covering the full lake polygon (not chips), for all 9 lakes. Hand them to Violet.
- Done when: 18 composites (9 lakes × 2 years) are on Drive with true-colour previews.

**M7 — Documentation**
- Do: write report section 5 (sources, cloud masking, label rules, tiling, cleaning, split, class balance table). Write a `DATASET.md` "datasheet": what's in it, how it was made, known biases.

---

### 6.4 Onyango Violet Atieno — ML Engineer (model training & evaluation)

Violet builds, trains and fairly evaluates the model, and uses it to produce the water maps for the two comparison years.

| ID | Task | Week |
|---|---|---|
| V1 | Data loader + non-ML baselines | 2–3 |
| V2 | U-Net training | 3–4 |
| V3 | Evaluation on held-out lakes | 4 |
| V4 | Error analysis | 4 |
| V5 | Inference on 2016 & 2025 + model areas | 4–5 |
| V6 | Model docs & report section | 5 |

**V1 — Data loader + baselines**
- Do: write a PyTorch `Dataset` that reads the chips via `manifest.csv`, normalises bands, and applies simple augmentations (flips, 90° rotations) **to training only**. Score two **non-ML baselines** on the val and test sets first:
  1. **MNDWI threshold:** MNDWI = (B3 − B11)/(B3 + B11); water if > 0.
  2. **Otsu threshold** on MNDWI per chip.
- Output: `src/model/dataset.py`, `src/model/baselines.py`, `outputs/results/baseline_scores.csv`.
- Done when: baseline scores exist. The model must beat these to be worth anything.

**V2 — U-Net training**
- Do: use `segmentation-models-pytorch`, U-Net with a ResNet-34 encoder (ImageNet weights; adapt the first layer to 6 input bands), loss = Dice + BCE, **ignore label 255**. Train on Colab GPU with early stopping on validation IoU. Log every run (settings + scores) in `docs/experiments.md`. Try at most 3–4 variants (e.g. with/without SWIR bands, different learning rates). Don't spend weeks tuning.
- Output: `src/model/train.py`, best weights on Drive (`models/unet_best.pth`), a training-curve figure.
- Done when: validation IoU has stopped improving, and the best run is recorded with its exact settings and seed.

**V3 — Evaluation on held-out lakes**
- Do: evaluate the best model **once** on the test lakes (Nakuru, Magadi, Ol Bolossat), on both the JRC-labelled chips and the **hand-corrected 40 chips** (M5). Report per lake: **IoU, F1, precision, recall, and area error %**, next to the two baselines.
- Output: `src/model/evaluate.py`, `outputs/results/model_scores.csv`.
- Done when: the results table is complete. Report it honestly even where the model loses.

**V4 — Error analysis**
- Do: show 6–8 example chips with *image | label | prediction | error map* for the best and worst cases. Group the errors (salt crust, swamp vegetation, cloud remnants, shallow edges, turbid water).
- Output: `outputs/figures/model_errors/`.
- Done when: each error type has an example and an explanation.

**V5 — Inference & model areas**
- Do: run the model over the full 2016 and 2025 composites (M6) with sliding windows and overlap, stitching predictions so there are no seams at tile edges. Keep only water inside each lake polygon and connected to the main body. Compute area (convert pixel area properly, or reproject to EPSG:6933 first). Output per contract C4.
- Done when: 18 prediction maps + `model_areas.csv` exist, with a visual check that they show no visible tile seams.

**V6 — Docs & report**
- Do: write report section 6 (model, training setup, results tables, error analysis) and a `MODEL.md` (inputs, outputs, scores, limits, how to run inference).

---

### 6.5 Otieno Juliet Jaoko — Validation, Analysis & Visualisation

Juliet turns the numbers into answers: are they right, which lakes are most vulnerable, and how do we show it clearly.

| ID | Task | Week |
|---|---|---|
| J1 | Literature & reference values | 1–2 |
| J2 | Hand-corrected test set (with Melissa) | 3 |
| J3 | Validation against water levels | 4–5 |
| J4 | Vulnerability ranking | 5 |
| J5 | Maps & figures | 5 |
| J6 | Dashboard / web map | 5–6 |
| J7 | Report section & limitations | 5–6 |

**J1 — Literature & reference values**
- Do: build `docs/reference_values.csv` of **published** lake areas and levels with full citations: the Rift lakes rising study (Herrnegger et al.), RCMRD's Rift Valley lakes analysis, AFP's Baringo analysis, Lake Turkana and Gibe III studies, Ol Bolossat and Kamnarok reports. Also write a 1-page Kenya context summary that Gift can use in the introduction.
- Done when: at least one published reference value exists for at least 5 of the 9 lakes.

**J2 — Hand-corrected test set (with Melissa)**
- See M5. Juliet corrects 20 chips and cross-checks Melissa's 20.

**J3 — Validation**
- Do: register on DAHITI and download water level time series for the study lakes that have them (Turkana, Baringo, Naivasha, etc.). For each lake, check that **area goes up when level goes up**: scatter plot of yearly mean level vs WOfS area, plus a Pearson/Spearman correlation. Compare WOfS areas and model areas (2016, 2025) with the published values from J1.
- Output: `src/analysis/validate.py`, `outputs/results/validation.csv`, scatter plots.
- Done when: each lake has a validation verdict (good / partial / no independent data) with a reason.

**J4 — Vulnerability ranking**
- Do: for each lake, from the **reliable** WOfS years only:
  - % change 2010 → 2025 and 2016 → 2025 (the latter compared with the model's numbers).
  - Long-term trend with **Theil–Sen slope** and **Mann–Kendall test** (`pymannkendall`), which handle noisy data and outliers.
  - Direction: expanding / shrinking / stable (stable = trend not significant at p < 0.05).
  - Confidence: high / medium / low, based on validation (J3), model–WOfS agreement, and lake type (swamp or saline = lower confidence).
- Output: `outputs/results/vulnerability_ranking.csv` (contract C5).
- Done when: every lake has a direction, a rank and a confidence, with the reasoning written down.

**J5 — Maps & figures**
- Do: a before/after map per lake (2016 vs 2025 water outline over the satellite image), a Kenya overview map with lakes coloured by direction of change, and the final ranking chart. Use consistent colours (e.g. blue = expanding, orange = shrinking, grey = stable) and check they're colour-blind safe.
- Output: `outputs/figures/final/`.

**J6 — Dashboard / web map**
- Do: a small **Streamlit** app (or a static Leaflet page): pick a lake, see its area chart, before/after outlines, and ranking info. Deploy it free (Streamlit Community Cloud or GitHub Pages).
- Done when: there's a public link in the README that works on a phone.

**J7 — Report section & limitations**
- Do: write report section 7 (validation and ranking). Draft section 8 (limitations & ethics) with input from everyone. Cover: label noise from JRC; swamp lakes (Ol Bolossat) and saline/soda lakes (Magadi, Bogoria) being hard to map; cloud gaps; area alone doesn't capture water quality or depth; and the project is not a replacement for ground surveys or official flood warnings.

---

## 7. Week-by-week checklist

### Week 1 — Setup & design
- [ ] Kickoff meeting: confirm roles, timeline, contracts (§3) — **all**
- [x] Repo, board, ruleset, PR checks — Gift (G1) · [ ] shared Drive folder, member invites
- [x] `lakes.geojson` — Gift (G2)
- [ ] Earth Engine + Colab "hello world" by everyone — Gift (G3) / all
- [ ] Start WOfS fetch — Aneselmus (A1)
- [ ] Start Sentinel-2 composites — Melissa (M1)
- [ ] Read up on U-Net and `segmentation-models-pytorch`; set up a training notebook skeleton — Violet
- [ ] Literature & reference values — Juliet (J1)
- **M1 check:** every member has merged at least one PR.

### Week 2 — Data
- [ ] Areas + quality flags for all lakes → `wofs_areas.csv` — Aneselmus (A2, A3)
- [ ] Composites + JRC labels for training years — Melissa (M1, M2)
- [ ] Data loader + baselines on the first chips — Violet (V1)
- [ ] Reference values done — Juliet (J1)
- [ ] Integration check M2 — Gift (G5)

### Week 3 — Data → Model
- [ ] Full chip dataset, cleaned, split, checked — Melissa (M3, M4)
- [ ] Hand-corrected 40 test chips — Melissa + Juliet (M5, J2)
- [ ] Inference composites 2016 & 2025 — Melissa (M6)
- [ ] JRC cross-check + baseline charts — Aneselmus (A4, A5)
- [ ] Baseline scores done; start U-Net training — Violet (V1, V2)
- [ ] Integration check M3 — Gift

### Week 4 — Model
- [ ] U-Net trained, test-set evaluation, error analysis — Violet (V2–V4)
- [ ] Inference + model areas — Violet (V5)
- [ ] Start validation against DAHITI — Juliet (J3)
- [ ] Dataset docs — Melissa (M7)
- [ ] Report sections 2–3 drafted — Gift (G6)
- [ ] Integration check M4 — Gift

### Week 5 — Analysis
- [ ] Validation done, ranking done — Juliet (J3, J4)
- [ ] Maps, figures, dashboard draft — Juliet (J5, J6)
- [ ] Every member's report section drafted (sections 4–7)
- [ ] Integration check M5 — Gift

### Week 6 — Finish
- [ ] Report edited and complete — Gift (G6) + all review
- [ ] Slides + rehearsal — Gift (G7) + all
- [ ] Dashboard deployed — Juliet (J6)
- [ ] Fresh-machine reproducibility test — Gift (G8) with Juliet/Melissa
- [ ] Contributions table filled honestly — all
- [ ] Repo tagged `v1.0`, submission made — Gift

---

## 8. Risks and what we'll do about them

| Risk | Likelihood | Plan |
|---|---|---|
| Someone falls behind or goes quiet | Medium | 24-hour blocker rule; weekly check-in; Gift re-assigns or pairs after 1 week behind. Each role has a backup: Aneselmus ↔ Juliet, Melissa ↔ Violet, Gift ↔ Juliet. |
| Earth Engine quota runs out (Community tier) | Low–Medium | Export results once, then reuse the files; keep areas small (lake polygons only); don't rerun big exports for no reason. |
| Colab GPU limits | Medium | Small chips, ResNet-34, early stopping; save checkpoints to Drive so a disconnect doesn't lose progress. |
| Clouds leave holes in composites | Medium | Widen the window to Dec–Mar for that lake-year; mark leftover holes as 255 (ignore). |
| JRC labels wrong in places | High (expected) | That's why we have the hand-corrected test set (M5); report it as a known limitation. |
| Swamp (Ol Bolossat) and salt lakes (Magadi) map badly | High (expected) | Treat them as deliberate hard test cases; report honestly; lower confidence in the ranking. |
| Model doesn't beat the MNDWI baseline | Possible | Still a valid result if reported honestly; analyse why in V4. The baseline area series (A2) still answers the main question. |
| Integration breaks at the end | Medium | Contracts in §3 + integration checks at every milestone. |
| Data leakage (same lake in train and test) | Medium if careless | Split by lake (C3); `check_dataset.py` fails if a lake appears in two splits. |

---

## 9. Final "definition of done" checklist (go through it before submitting)

**Repository**
- [ ] README: overview, results summary + main chart, setup steps, how to run each stage, links to dashboard, data and model weights
- [ ] `requirements.txt` installs cleanly on a fresh machine
- [ ] Every stage runs from a command-line script (not only notebooks)
- [ ] No secrets, API keys or large data files committed
- [ ] Release tagged `v1.0`

**Data**
- [ ] `lakes.geojson` (9 lakes, all fields)
- [ ] `wofs_areas.csv` with quality flags; no fake zeros
- [ ] `jrc_areas.csv` cross-check
- [ ] Chip dataset + manifest + `DATASET.md`; split by lake
- [ ] 40 hand-corrected test chips

**Model**
- [ ] Baseline scores (MNDWI, Otsu)
- [ ] U-Net scores on held-out lakes, both label sets, per lake
- [ ] Error analysis figures
- [ ] 2016 & 2025 predictions for all 9 lakes + `model_areas.csv`
- [ ] `MODEL.md` + weights on Drive

**Analysis**
- [ ] Validation results per lake
- [ ] `vulnerability_ranking.csv` with direction, trend, significance, confidence
- [ ] Before/after maps, Kenya overview map, ranking chart
- [ ] Dashboard live

**Write-up**
- [ ] Report complete (all 11 sections), figures captioned, sources cited
- [ ] Limitations & ethics section written honestly
- [ ] Slides + rehearsal done
- [ ] Individual contributions table agreed by all 5 members

---

## 10. Key data sources (for everyone's reference)

| Source | Used for | Access |
|---|---|---|
| Digital Earth Africa — WOfS annual summary | Baseline yearly areas 1984–2025 | STAC: `https://explorer.digitalearth.africa/stac` · S3: `s3://deafrica-services/wofs_ls_summary_annual/` (no account) |
| JRC Global Surface Water | Training labels; area cross-check | Earth Engine: `JRC/GSW1_4/MonthlyHistory`, `JRC/GSW1_4/YearlyHistory` |
| Sentinel-2 L2A (harmonised) | Model input imagery | Earth Engine: `COPERNICUS/S2_SR_HARMONIZED` |
| Cloud Score+ | Cloud masking | Earth Engine: `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED` |
| HydroLAKES | Lake outlines & IDs (already used to build `lakes.geojson`) | hydrosheds.org · Earth Engine: `projects/sat-io/open-datasets/HydroLakes/lake_poly_v10` |
| DAHITI (TU Munich) | Independent water levels for validation | dahiti.dgfi.tum.de (free registration) |
| RCMRD Geoportal | Local reference layers & prior analyses | geoportal.rcmrd.org |
| Published studies | Reference values | Herrnegger et al. (Rift lakes rising); RCMRD Rift Valley lakes analysis; Lake Turkana / Gibe III studies; Ol Bolossat reports |