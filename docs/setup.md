# Team setup checklist

Each member does the steps below once, then fills in **their own row** in the table as their **first pull request**.
That PR is how we confirm everyone can clone, branch, commit, open a PR and get it approved.

**Which account for what**

| Tool | Account |
|---|---|
| GitHub | your personal GitHub account |
| Google Colab, Google Drive, Earth Engine | your **UoN student account** (`@students.uonbi.ac.ke`) |

## Checklist

| Member | GitHub username | Repo cloned | Python 3.11 + venv | `pip install -r requirements.txt` | Drive shortcut | Colab works | Earth Engine test |
|---|---|---|---|---|---|---|---|
| Masila Muuo Gift | Giftmasil | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Aneselmus Oyando | | | | | | | |
| Angwenyi Melissa | | | | | | | |
| Onyango Violet Atieno | Favour0950 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Otieno Juliet Jaoko | | | | | | | |

---

## 1. GitHub

1. Accept the repo invite: check your email or <https://github.com/notifications>.
2. In **GitHub Desktop**: **File → Clone repository** → `Giftmasil/kenya-lakes-monitor` → choose a folder → **Clone**.

## 2. Python on your laptop

Open the repo folder in VS Code, open **Terminal → New Terminal**, and run:

```bash
python -m venv .venv
# Windows:    .venv\Scripts\activate
# Mac/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

You need **Python 3.11**. Check with `python --version`.
Only whoever trains or runs the model also needs `pip install -r requirements-ml.txt`.

## 3. Shared Google Drive

The folder `kenya-lakes` is shared with your UoN email. Big files (satellite images, training tiles, model weights, prediction maps) go here, **never in GitHub**.

To make it show up in Colab:

1. Open Google Drive with your **UoN account** → **Shared with me**.
2. Right-click **kenya-lakes** → **Organise → Add shortcut** (older menus: **Add shortcut to Drive**) → **My Drive**.
3. In Colab it will be at `/content/drive/MyDrive/kenya-lakes`.

What goes in which folder is explained in the README, under **Shared Google Drive: what goes where**.

## 4. Colab and Earth Engine

The team shares one Earth Engine project: **`kenya-lakes-monitor`** (Community tier, free, owned by Gift's UoN account). Your UoN email has already been added with the roles *Service Usage Consumer* and *Earth Engine Resource Writer*.

1. Open <https://colab.research.google.com> signed in with your **UoN account** (check the avatar at the top right).
2. Create a new notebook and run this cell:

```python
import ee
ee.Authenticate()                             # pick your @students.uonbi.ac.ke account in the pop-up
ee.Initialize(project="kenya-lakes-monitor")

n = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
       .filterBounds(ee.Geometry.Point(36.35, -0.77))     # Lake Naivasha
       .filterDate("2025-01-01", "2025-03-01")
       .size().getInfo())
print("Sentinel-2 images over Lake Naivasha, Jan–Feb 2025:", n)
```

3. If it prints a number (about **24**), Colab and Earth Engine both work.

**If you get a permission error:** check that Colab *and* the `ee.Authenticate()` pop-up both used your **UoN** account, not a personal Gmail. If you're signed into several Google accounts in the same browser, a separate Chrome profile for your UoN account avoids mix-ups.

## 5. Your first pull request

1. In GitHub Desktop: **Current branch → New branch**, named `setup/<your-first-name>` (e.g. `setup/violet`).
2. Open this file (`docs/setup.md`) and fill in **your row**: your GitHub username, then ✅ for each step that worked. Leave a cell blank if a step didn't work, and say so in the group chat.
3. Commit with a message like `Setup checklist: Violet`, then click **Publish branch → Create Pull Request**.
4. On GitHub, fill in the PR template and ask your **review partner** to approve:

   | You | Your reviewer |
   |---|---|
   | Aneselmus | Juliet |
   | Juliet | Aneselmus |
   | Melissa | Violet |
   | Violet | Melissa |
   | Gift | Juliet |

5. Once the automatic **checks** pass ✅ and your reviewer approves, click **Squash and merge**.

If two people edit this table at the same time, the second PR may show a merge conflict. Click **Resolve conflicts** on GitHub, keep **both** rows, then mark it resolved. Or ask Gift for help.

## When you're done

Read your section in [`docs/project-plan.md`](project-plan.md) (section 6) and start on your first task. Push at least once a week, and say in the group chat if you're stuck for more than a day.
