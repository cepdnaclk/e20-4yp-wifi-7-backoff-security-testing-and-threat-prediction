#!/usr/bin/env bash
# monitor_parallel.sh
# Real-time monitoring of parallel data generation with integrity checks

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

clear
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     WP9 Pilot - Parallel Generation Monitor                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if parallel process is running
if [ -f training_data/pilot_parallel.pid ]; then
    PID=$(cat training_data/pilot_parallel.pid)
    if ps -p $PID > /dev/null 2>&1; then
        runtime=$(ps -p $PID -o etime --no-headers | xargs)
        echo "✅ Status: RUNNING (PID: $PID, Runtime: $runtime)"
    else
        echo "⚠️  Status: STOPPED"
    fi
else
    echo "⚠️  Status: NOT STARTED"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "OVERALL PROGRESS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Count completed scenarios
completed=$(find training_data/scenarios -name "*.json" -type f 2>/dev/null | wc -l)
echo "Completed scenarios: $completed / 30"
echo ""

# Show progress bar
progress=$((completed * 100 / 30))
bar_length=50
filled=$((progress * bar_length / 100))
empty=$((bar_length - filled))
printf "["
printf "%${filled}s" | tr ' ' '='
printf "%${empty}s" | tr ' ' '-'
printf "] %d%%\n" $progress

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ACTIVE SIMULATIONS (Real-time)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check currently running scenarios
active_count=0
for artifact_dir in sim/ns3/artifacts/pilot-*/; do
    if [ -d "$artifact_dir" ]; then
        exp_id=$(basename "$artifact_dir")
        json_file="${artifact_dir}mlo_output.json"

        # Check if scenario is in progress (JSON exists but not in training_data)
        if [ -f "$json_file" ]; then
            windows=$(grep -c '"window":' "$json_file" 2>/dev/null || echo "0")

            # Check if completed (copied to training_data)
            if [ -f "training_data/scenarios/normal/light/${exp_id}.json" ] || \
               [ -f "training_data/scenarios/positive_attack/*/${exp_id}.json" ] || \
               [ -f "training_data/scenarios/negative_attack/*/${exp_id}.json" ]; then
                # Already completed and copied
                continue
            else
                # Still in progress
                if [ "$windows" -gt 0 ] && [ "$windows" -lt 2000 ]; then
                    active_count=$((active_count + 1))
                    size=$(stat -c%s "$json_file" 2>/dev/null || echo "0")
                    size_kb=$((size / 1024))
                    progress=$((windows * 100 / 2000))

                    # Extract seed from exp_id
                    seed=$(echo "$exp_id" | grep -oP 'seed\K\d+' || echo "?")

                    printf "  🔄 Scenario %-2s: %4d/2000 windows (%3d%%) - %4d KB\n" \
                        "$seed" "$windows" "$progress" "$size_kb"
                fi
            fi
        fi
    fi
done

if [ $active_count -eq 0 ]; then
    echo "  No active simulations (between batches or completed)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DATA INTEGRITY CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check old scenarios (1-8)
old_good=0
old_bad=0
for seed in 1 2 3 4 5 6 7 8; do
    if [ $seed -eq 1 ]; then
        file="training_data/scenarios/normal/light/pilot-20260213-normal-normal-seed${seed}.json"
    else
        file="training_data/scenarios/normal/light/pilot-20260214-normal-normal-seed${seed}.json"
    fi

    if [ -f "$file" ]; then
        windows=$(grep -c '"window":' "$file" 2>/dev/null || echo "0")
        if [ "$windows" -eq 14000 ]; then
            old_good=$((old_good + 1))
        else
            old_bad=$((old_bad + 1))
        fi
    fi
done

echo "Old scenarios (1400s): $old_good ✅ / $((old_good + old_bad)) total"

# Check new scenarios (9+)
new_good=0
new_bad=0
for file in training_data/scenarios/normal/light/pilot-*-seed{9..15}.json \
            training_data/scenarios/positive_attack/*/pilot-*.json \
            training_data/scenarios/negative_attack/*/pilot-*.json; do
    if [ -f "$file" ]; then
        windows=$(grep -c '"window":' "$file" 2>/dev/null || echo "0")
        if [ "$windows" -ge 1800 ] && [ "$windows" -le 2200 ]; then
            new_good=$((new_good + 1))
        else
            new_bad=$((new_bad + 1))
        fi
    fi
done

if [ $new_good -gt 0 ]; then
    echo "New scenarios (200s):  $new_good ✅ / $((new_good + new_bad)) total"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE BREAKDOWN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

normal_count=$(find training_data/scenarios/normal -name "*.json" 2>/dev/null | wc -l)
positive_count=$(find training_data/scenarios/positive_attack -name "*.json" 2>/dev/null | wc -l)
negative_count=$(find training_data/scenarios/negative_attack -name "*.json" 2>/dev/null | wc -l)

echo "Phase 1 (Normal):   $normal_count / 15"
echo "Phase 2 (Positive): $positive_count / 8"
echo "Phase 3 (Negative): $negative_count / 7"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SYSTEM RESOURCES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# CPU usage
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
echo "CPU Usage: ${cpu_usage}%"

# Docker containers
docker_count=$(docker ps --filter "ancestor=ndt/ns3:local" 2>/dev/null | tail -n +2 | wc -l)
echo "Active Docker containers: $docker_count"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Commands:"
echo "  Live log: tail -f training_data/pilot_parallel.log"
echo "  Rerun:    ./scripts/monitor_parallel.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
