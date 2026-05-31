#!/usr/bin/env bash
#
# Regenerate all analysis plots and results.
#
# Usage:
#   ./scripts/run_all.sh          # run all scripts, save plots
#   ./scripts/run_all.sh --quick  # skip the slow ones (formation_scaling, span_chord_sweep)

set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-.venv/bin/python}"
QUICK=false
[[ "${1:-}" == "--quick" ]] && QUICK=true

run() {
    local name="$1"
    shift
    echo "=== $name ==="
    time "$PYTHON" "$@" --save
    echo ""
}

echo "Running all analysis scripts..."
echo "Python: $PYTHON"
echo ""

# Fast scripts (< 30s each)
run "converged_sweep"        scripts/converged_sweep.py &
run "energy_timeline"        scripts/energy_timeline.py &
run "cost_comparison"        scripts/cost_comparison.py &
run "climb_profile"          scripts/climb_profile.py &
run "formation_drag"         scripts/formation_drag_analysis.py &
run "sweep_single_vs_form"   scripts/sweep_single_vs_formation.py &
run "sensitivity"            scripts/sensitivity_analysis.py &
wait

# Slow scripts (1-10 min each)
if $QUICK; then
    echo "=== SKIPPING slow scripts (--quick) ==="
else
    run "formation_scaling"  scripts/formation_scaling.py &
    run "span_chord_sweep"   scripts/span_chord_sweep.py &
    wait
fi

echo ""
echo "=== ALL DONE ==="
echo ""
echo "Plots saved to docs/formation_flight/"
ls -1 docs/formation_flight/*.png
