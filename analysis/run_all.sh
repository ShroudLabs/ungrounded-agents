#!/usr/bin/env bash
# Regenerate every number and figure in the paper from raw per-trial data.
set -euo pipefail
cd "$(dirname "$0")"
python3 reproduce_paper.py            > ../figures/descriptives.txt
python3 stats_final.py                > ../figures/corrected_stats.txt
python3 figures.py
echo "Done. Tables in ../figures/*.txt, figures in ../figures/*.pdf"
