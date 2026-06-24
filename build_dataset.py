"""
Apply draft labels to data/to_label.csv and produce labeled_dataset.csv
(repo root) as ONE complete, non-pre-split file. The training notebook
performs the 70/15/15 split automatically, so we do not pre-split here.

Columns: text, label, notes, thread_type, id
  - text, label: required by the notebook
  - notes: filled only for genuinely difficult cases (blank otherwise)
  - thread_type, id: retained for error analysis / provenance

LABELS is indexed by row number n (1-based) from to_label.csv.
  a = analysis, h = hot_take, r = reaction
"""

import csv

CODE = {"a": "analysis", "h": "hot_take", "r": "reaction"}

# Notes for difficult cases encountered during annotation, keyed by comment id.
NOTES = {
    "orl5524": "Hardest edge case (reaction vs analysis): names the result an 'upset' "
    "without explaining why. Decided reaction per the decision rule — no evidence, no claim.",
    "otf5vik": "Borderline analysis vs hot_take: ranty, insult-heavy ('utter dogshite') but "
    "makes a checkable season-long claim (bad vs low blocks). Decided analysis — substance is verifiable.",
    "orkcdr8": "Borderline hot_take vs analysis: names Euros + WC which looks like evidence, but "
    "cited to back a 'Turkey always chokes' verdict, not to explain why. Decided hot_take — specifics are decorative.",
    "orypdlp": "Borderline reaction vs hot_take: witty squad-depth quip. Decided reaction — "
    "banter with no disputable claim being argued.",
    "ot9hf47": "Borderline hot_take vs analysis: rant with embedded stats (90M, 500M clause, penalty miss). "
    "Decided hot_take — accusatory framing, stats are decorative dunks, not genuine reasoning.",
    "ot91oen": "Contrast to ot9hf47: same kind of facts but measured, explanatory framing ('in part because'). "
    "Decided analysis — genuine reasoning, not a dunk.",
}

# Draft labels for n = 1..254 (applying the planning.md decision rule).
# Grouped in rows of 10 (n: 1-10, 11-20, ...) to keep the count exact.
LABELS = (
    list("ahaarhraar")  # 1-10
    + list("rrahhhrhrr")  # 11-20
    + list("rhahraaaaa")  # 21-30
    + list("rraaaharhr")  # 31-40
    + list("aaaaharaha")  # 41-50
    + list("hahhahaarh")  # 51-60
    + list("hrhraarrah")  # 61-70
    + list("hrhrrhrarh")  # 71-80
    + list("hhrraaahra")  # 81-90
    + list("hrrraaahrr")  # 91-100
    + list("rarhhhrrar")  # 101-110
    + list("hhrrarhaha")  # 111-120
    + list("rarrraarha")  # 121-130
    + list("harraaaaar")  # 131-140
    + list("rhhaahaaar")  # 141-150
    + list("ararrarhrr")  # 151-160
    + list("rharahaarr")  # 161-170
    + list("harhraahrr")  # 171-180
    + list("rhhrrrahah")  # 181-190
    + list("rharhhraar")  # 191-200
    + list("rhrhrahrrr")  # 201-210
    + list("rrarrahhhr")  # 211-220
    + list("rhrhrahrha")  # 221-230
    + list("haarrraahr")  # 231-240
    + list("rrrrarhrrh")  # 241-250
    + list("rhhr")  # 251-254
)

assert len(LABELS) == 254, f"expected 254 labels, got {len(LABELS)}"

rows = list(csv.DictReader(open("data/to_label.csv", encoding="utf-8")))
assert len(rows) == 254

for r in rows:
    r["label"] = CODE[LABELS[int(r["n"]) - 1]]
    r["notes"] = NOTES.get(r["id"], "")

rows.sort(key=lambda r: int(r["n"]))

with open("labeled_dataset.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["text", "label", "notes", "thread_type", "id"])
    w.writeheader()
    for r in rows:
        w.writerow(
            {
                "text": r["text"],
                "label": r["label"],
                "notes": r["notes"],
                "thread_type": r["thread_type"],
                "id": r["id"],
            }
        )

# report
from collections import Counter

c = Counter(r["label"] for r in rows)
total = len(rows)
print(f"Wrote {total} rows -> labeled_dataset.csv (single file, not pre-split)")
print("Label distribution:")
for lab in ("analysis", "hot_take", "reaction"):
    pct = c[lab] / total * 100
    print(f"  {lab:<10} {c[lab]:>3}  ({pct:.0f}%)")
top = max(c.values()) / total * 100
print(f"Largest class: {top:.0f}%  ->  {'OK (<70%)' if top < 70 else 'IMBALANCE (>70%)'}")
print(f"Difficult-case notes attached: {sum(1 for r in rows if r['notes'])}")
