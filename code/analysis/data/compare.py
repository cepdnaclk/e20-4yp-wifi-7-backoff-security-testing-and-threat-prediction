# import json
# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns # Optional, but makes it prettier
# import numpy as np

# # --- CONFIGURATION ---
# # ENSURE THESE FILENAMES MATCH YOUR DATA
# FILE_NORMAL = "Wifi7_Datasets/Normal/apple_0.json"
# FILE_ATTACK = "Wifi7_Datasets/Attack/apple_5000.json"

# def load_and_process(filepath, label):
#     try:
#         with open(filepath, 'r') as f:
#             data = json.load(f)
#     except FileNotFoundError:
#         print(f"Error: Could not find {filepath}.")
#         return pd.DataFrame()

#     processed_rows = []
    
#     for entry in data:
#         # The JSON is now FLAT (calculated in C++), so we just map keys directly.
#         row = {
#             "Time (s)": entry['window'] * 0.1,
#             "Scenario": label,
            
#             # --- Network Layer Metrics ---
#             "Throughput (Mbps)": entry.get('net_throughput_mbps', 0),
#             "Avg Latency (ms)": entry.get('net_avg_delay_ms', 0),
#             "Avg Jitter (ms)": entry.get('net_avg_jitter_ms', 0),
#             "Packet Loss Ratio": entry.get('net_packet_loss_ratio', 0),
#             "Active Flows": entry.get('net_active_flows', 0),
            
#             # --- MAC/PHY Layer Metrics ---
#             "Total Tx Packets": entry.get('mac_total_tx', 0),
#             "Total Rx Packets": entry.get('mac_total_rx', 0),
#             "MAC ACK Count": entry.get('mac_total_ack', 0),
#             "MAC Retransmissions": entry.get('mac_total_retrans', 0),
#             "MAC Layer Drops": entry.get('mac_drop_count', 0),
#             "PHY Layer Drops": entry.get('phy_drop_count', 0),
            
#             # --- Attack Indicators ---
#             "Avg Backoff Slots": entry.get('avg_backoff_slots', 0),
#             "Channel Busy Ratio": entry.get('channel_busy_ratio', 0)
#         }
#         processed_rows.append(row)
        
#     return pd.DataFrame(processed_rows)

# # --- MAIN EXECUTION ---
# print("Processing Normal Dataset...")
# df_normal = load_and_process(FILE_NORMAL, "Normal Baseline")

# print("Processing Attack Dataset...")
# df_attack = load_and_process(FILE_ATTACK, "Backoff Attack")

# if df_normal.empty or df_attack.empty:
#     print("CRITICAL ERROR: One or both data files are missing or empty.")
#     exit()

# # Define the full list of metrics to plot
# metrics_to_plot = [
#     # Row 1: The Main KPIs
#     "Throughput (Mbps)", "Avg Latency (ms)", "Avg Jitter (ms)",
    
#     # Row 2: The Attack Indicators
#     "Avg Backoff Slots", "Channel Busy Ratio", "Packet Loss Ratio",
    
#     # Row 3: Error Counters
#     "MAC Retransmissions", "MAC Layer Drops", "PHY Layer Drops",
    
#     # Row 4: Traffic Volume
#     "Total Tx Packets", "Total Rx Packets", "MAC ACK Count",
    
#     # Row 5: Network State
#     "Active Flows"
# ]

# # Create Grid: 5 Rows x 3 Columns
# plt.style.use('bmh') # Clean visual style
# fig, axes = plt.subplots(5, 3, figsize=(18, 22)) # Big canvas
# fig.suptitle('WiFi 7 MLO Attack Analysis: Full Parameter Set', fontsize=22, weight='bold')

# # Flatten axes array for easy looping
# axes_flat = axes.flatten()

# for i, metric in enumerate(metrics_to_plot):
#     if i >= len(axes_flat): break # Safety check
    
#     ax = axes_flat[i]
    
#     # Plot Normal (Green)
#     ax.plot(df_normal["Time (s)"], df_normal[metric], 
#             label="Normal", color="#2ca02c", alpha=0.8, linewidth=1.5)
            
#     # Plot Attack (Red)
#     ax.plot(df_attack["Time (s)"], df_attack[metric], 
#             label="Attack", color="#d62728", alpha=0.8, linewidth=1.5)
    
#     ax.set_title(metric, fontsize=12, weight='bold')
#     ax.tick_params(axis='both', which='major', labelsize=9)
#     ax.legend(loc='upper right', fontsize=8)
    
#     # Add light grid
#     ax.grid(True, linestyle='--', alpha=0.7)

# # Hide any empty subplots
# for j in range(len(metrics_to_plot), len(axes_flat)):
#     fig.delaxes(axes_flat[j])

# plt.tight_layout(rect=[0, 0.03, 1, 0.96]) # Adjust for title
# plt.savefig("full_analysis_results.png", dpi=300)
# print("Success! Saved visualization to 'full_analysis_results.png'")
# plt.show()





















# ENSURE THESE FILENAMES MATCH YOUR DATA
FILE_NORMAL = "apple_0.json"
FILE_ATTACK = "Wifi7_Datasets/Attack/apple_5000.json"



import json
import pandas as pd
import matplotlib.pyplot as plt
import math

# ==========================================
# CONFIGURATION: 3 DATASETS (RGB COLORS)
# ==========================================
DATASETS = [
    # (Filename,          Legend Label,       Color)
    ("Wifi7_Datasets/Normal/session_1_scenario_1.json",    "Normal (Bias 0)",    "green"),  # G
    ("Wifi7_Datasets/Attack/session_1_scenario_1_bias_500.json",  "Attack (Bias -5000)",  "blue"),   # B
    ("Wifi7_Datasets/Attack/session_1_scenario_1_bias_neg500.json", "Attack (Bias 5000)", "red")     # R
]

def load_data(filepath, label):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Warning: '{filepath}' not found. Skipping.")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    if not df.empty:
        df['Scenario'] = label
        df['Time (s)'] = df['window'] * 0.1
    return df

# --- MAIN EXECUTION ---
dfs = []
scenario_colors = {}

print("Loading Datasets...")
for filename, label, color in DATASETS:
    df = load_data(filename, label)
    if not df.empty:
        dfs.append(df)
        scenario_colors[label] = color

if not dfs:
    print("Error: No data loaded.")
    exit()

df_final = pd.concat(dfs, ignore_index=True)

# 1. DYNAMICALLY FIND ALL METRICS
# We exclude non-metric columns like 'window', 'bias', 'Scenario', 'Time (s)'
non_metric_cols = ['window', 'bias', 'Scenario', 'Time (s)']
all_columns = df_final.columns.tolist()
metric_columns = [c for c in all_columns if c not in non_metric_cols and pd.api.types.is_numeric_dtype(df_final[c])]

print(f"Found {len(metric_columns)} metrics to plot: {metric_columns}")

# 2. CALCULATE GRID SIZE
num_plots = len(metric_columns)
cols = 3
rows = math.ceil(num_plots / cols)

# 3. PLOT EVERYTHING
plt.style.use('bmh')
fig, axes = plt.subplots(rows, cols, figsize=(18, 4 * rows))
fig.suptitle('WiFi 7 MLO Analysis: Full Parameter Set (RGB)', fontsize=22, weight='bold')

axes_flat = axes.flatten()

for i, metric in enumerate(metric_columns):
    ax = axes_flat[i]
    
    # Plot each scenario present in the data
    for label, color in scenario_colors.items():
        subset = df_final[df_final['Scenario'] == label]
        if not subset.empty:
            ax.plot(subset["Time (s)"], subset[metric], 
                    label=label, color=color, alpha=0.8, linewidth=2)
    
    ax.set_title(metric, fontsize=11, weight='bold')
    ax.legend(fontsize=9, loc='upper right')
    ax.grid(True, linestyle='--', alpha=0.7)

# Remove empty subplots if grid is larger than num_plots
for j in range(num_plots, len(axes_flat)):
    fig.delaxes(axes_flat[j])

plt.tight_layout(rect=[0, 0.03, 1, 0.96])
output_filename = "full_rgb_analysis.png"
plt.savefig(output_filename, dpi=300)
print(f"Graph saved as '{output_filename}'")
plt.show()




















# import json
# import pandas as pd
# import matplotlib.pyplot as plt
# import math
# import os

# # ==========================================
# # CONFIGURATION
# # ==========================================
# DATASETS = [
#     # (Filename,          Legend Label,          Color)
#     ("test_00000.json",   "Normal (Bias 0)",     "green"),
#     ("test_05000.json",   "Attack (Bias 5000)",  "blue"),
#     ("test_min5000.json", "Attack (Bias -5000)", "red")
# ]

# # Mapping raw JSON keys (from C++) to readable Graph Titles
# COLUMN_MAPPING = {
#     "net_throughput_mbps": "Throughput (Mbps)",
#     "net_avg_delay_ms": "Avg Latency (ms)",
#     "net_avg_jitter_ms": "Avg Jitter (ms)",
#     "net_packet_loss_ratio": "Packet Loss Ratio",
#     "net_active_flows": "Active Flows",
#     "mac_total_tx": "Total Tx Packets",
#     "mac_total_rx": "Total Rx Packets",
#     "mac_total_ack": "MAC ACK Count",
#     "mac_total_retrans": "MAC Retransmissions",
#     "mac_drop_count": "MAC Layer Drops",
#     "phy_drop_count": "PHY Layer Drops",
#     "avg_backoff_slots": "Avg Backoff Slots",
#     "channel_busy_ratio": "Channel Busy Ratio"
# }

# def load_data(filepath, label):
#     if not os.path.exists(filepath):
#         print(f"Warning: File '{filepath}' not found. Check the filename!")
#         return pd.DataFrame()
        
#     try:
#         with open(filepath, 'r') as f:
#             data = json.load(f)
#     except json.JSONDecodeError:
#         print(f"Error: '{filepath}' is not a valid JSON file.")
#         return pd.DataFrame()

#     df = pd.DataFrame(data)
#     if not df.empty:
#         df['Scenario'] = label
#         df['Time (s)'] = df['window'] * 0.1
        
#         # Rename keys to nice titles; this also filters out unwanted columns
#         df.rename(columns=COLUMN_MAPPING, inplace=True)
        
#     return df

# # --- MAIN EXECUTION ---
# dfs = []
# scenario_colors = {}

# print("Loading Datasets...")
# for filename, label, color in DATASETS:
#     df = load_data(filename, label)
#     if not df.empty:
#         dfs.append(df)
#         scenario_colors[label] = color

# if not dfs:
#     print("CRITICAL ERROR: No data loaded. Please run the NS-3 simulation first.")
#     exit()

# df_final = pd.concat(dfs, ignore_index=True)

# # Find which columns actually exist in the loaded data
# metrics_to_plot = [title for title in COLUMN_MAPPING.values() if title in df_final.columns]

# print(f"Plotting {len(metrics_to_plot)} variables...")

# # Calculate Grid Size
# num_plots = len(metrics_to_plot)
# cols = 3
# rows = math.ceil(num_plots / cols)

# # Plotting
# plt.style.use('bmh')
# fig, axes = plt.subplots(rows, cols, figsize=(18, 4 * rows))
# fig.suptitle('WiFi 7 MLO Analysis: Full Parameter Set', fontsize=22, weight='bold')

# axes_flat = axes.flatten()

# for i, metric in enumerate(metrics_to_plot):
#     ax = axes_flat[i]
    
#     # Plot each scenario
#     for label, color in scenario_colors.items():
#         subset = df_final[df_final['Scenario'] == label]
#         if not subset.empty:
#             ax.plot(subset["Time (s)"], subset[metric], 
#                     label=label, color=color, alpha=0.8, linewidth=2)
    
#     ax.set_title(metric, fontsize=11, weight='bold')
#     ax.legend(fontsize=9, loc='upper right')
#     ax.grid(True, linestyle='--', alpha=0.7)
    
#     # --- Special Scale Handling ---
    
#     # 1. Backoff Slots: Handle massive values (Billions) vs Normal (Tens)
#     if metric == "Avg Backoff Slots":
#         max_val = df_final[metric].max()
#         if max_val > 10000: 
#             # Use symlog to handle 0 and huge numbers simultaneously without error
#             ax.set_yscale('symlog') 
#             ax.set_title(metric + " (Log Scale)", fontsize=11, weight='bold')
            
#     # 2. Packet Loss: Keep strictly between 0 and 1
#     if metric == "Packet Loss Ratio":
#         ax.set_ylim(-0.05, 1.05)

# # Remove empty subplots
# for j in range(num_plots, len(axes_flat)):
#     fig.delaxes(axes_flat[j])

# plt.tight_layout(rect=[0, 0.03, 1, 0.96])
# output_file = "final_rgb_visualization-test2.png"
# plt.savefig(output_file, dpi=300)
# print(f"Success! Graph saved as '{output_file}'. Open it to see the results.")
# plt.show()