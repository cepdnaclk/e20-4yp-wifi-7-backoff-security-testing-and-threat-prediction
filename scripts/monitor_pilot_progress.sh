#!/usr/bin/env bash
# monitor_pilot_progress.sh
# Monitor WP9 pilot study data generation progress

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo "WP9 Pilot Study Progress Monitor"
echo "========================================"
echo ""

# Check if generation is running
if [ -f training_data/pilot_generation.pid ]; then
    PID=$(cat training_data/pilot_generation.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Status: RUNNING (PID: $PID)"
    else
        echo "⚠️  Status: STOPPED (process not found)"
    fi
else
    echo "⚠️  Status: NOT STARTED (no PID file)"
fi

echo ""

# Count completed scenarios
normal_count=$(find training_data/scenarios/normal -name "*.json" 2>/dev/null | wc -l)
positive_count=$(find training_data/scenarios/positive_attack -name "*.json" 2>/dev/null | wc -l)
negative_count=$(find training_data/scenarios/negative_attack -name "*.json" 2>/dev/null | wc -l)
total_count=$((normal_count + positive_count + negative_count))

echo "Progress: $total_count / 30 scenarios complete"
echo ""
echo "Breakdown:"
echo "  Normal:    $normal_count / 15 ($(echo "scale=1; $normal_count * 100 / 15" | bc 2>/dev/null || echo "0")%)"
echo "  Positive:  $positive_count / 8 ($(echo "scale=1; $positive_count * 100 / 8" | bc 2>/dev/null || echo "0")%)"
echo "  Negative:  $negative_count / 7 ($(echo "scale=1; $negative_count * 100 / 7" | bc 2>/dev/null || echo "0")%)"
echo ""

# Progress bar
progress=$((total_count * 100 / 30))
bar_length=50
filled=$((progress * bar_length / 100))
empty=$((bar_length - filled))
printf "["
printf "%${filled}s" | tr ' ' '='
printf "%${empty}s" | tr ' ' '-'
printf "] %d%%\n" $progress

echo ""

# Estimated time remaining
if [ $total_count -gt 0 ]; then
    # Assuming 15 min per scenario
    remaining=$((30 - total_count))
    minutes=$((remaining * 15))
    hours=$((minutes / 60))
    mins=$((minutes % 60))
    echo "Estimated time remaining: ~${hours}h ${mins}m"
fi

echo ""
echo "Latest activity (last 10 lines):"
echo "----------------------------------------"
if [ -f training_data/pilot_generation.log ]; then
    tail -10 training_data/pilot_generation.log
else
    echo "(no log file yet)"
fi

echo ""
echo "========================================"
echo "Commands:"
echo "  Watch live: tail -f training_data/pilot_generation.log"
echo "  Rerun monitor: ./scripts/monitor_pilot_progress.sh"
echo "  View manifest: cat training_data/manifest_pilot.csv"
echo "========================================"
