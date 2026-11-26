# Decisions log

Every project decision, with its date and reason. Add new ones at the bottom.

| Date | Decision | Reason | Decided by |
|---|---|---|---|
| 2026-11-26 | Project: Kenyan lakes change monitor (not breast cancer detection) | Real, messy data; locally relevant; results can be checked against published studies | Group |
| 2026-11-26 | Study lakes: Baringo, Bogoria, Nakuru, Elementaita, Naivasha, Solai, Turkana, Ol Bolossat, Magadi | Mix of growing, shrinking, dam-affected and hard (soda/swamp) lakes; Lake Victoria out of scope | Group |
| 2026-11-26 | "Vulnerable" = largest change in either direction | Many Kenyan lakes are rising and flooding, not only shrinking | Group |
| 2026-11-26 | Baseline areas from Digital Earth Africa WOfS | Ready-made water maps for Africa, 1984–2025, free | Group |
| 2026-11-26 | Model: U-Net (PyTorch), not TensorFlow Object Detection API | The API in the book is deprecated; bounding boxes give poor area estimates | Group |
| 2026-11-26 | Dependencies via pip `requirements.txt` (not conda) | Works the same on Windows laptops and Colab | Gift |
| 2026-11-26 | Repo is public; all changes to `main` go through reviewed PRs | Free-plan branch protection only works on public repos | Gift |