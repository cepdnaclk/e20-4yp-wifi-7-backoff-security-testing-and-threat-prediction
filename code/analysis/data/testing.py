# import json
# import os
# import math
# import pandas as pd
# import matplotlib.pyplot as plt
# import numpy as np

# # ==========================================
# # 1. USER CONFIGURATION
# # ==========================================
# # Instructions: Add as many files as you want to this list.
# # Format: ("FileName.json", "Legend Label", "Color")

# DATASETS = [
#     # --- Normal Scenario ---
#     ("Wifi7_Datasets/Normal/session_1_scenario_1.json",           "Normal (Bias 0)",    "green"),

#     # --- Attack Scenarios (Add or remove lines here) ---
#     ("Wifi7_Datasets/Normal/session_1_scenario_1_bias_100.json",  "Attack (Bias 100)",  "orange"),
#     ("Wifi7_Datasets/Normal/session_1_scenario_1_bias_500.json",  "Attack (Bias 500)",  "purple"),
#     ("Wifi7_Datasets/Normal/session_1_scenario_1_bias_1000.json",  "Attack (Bias 500)",  "purple"),
#     ("Wifi7_Datasets/Normal/session_1_scenario_1_bias_5000.json", "Attack (Bias 5000)", "blue"),
    
#     # --- Aggressive Scenarios (Negative Bias) ---
#     ("Wifi7_Datasets/Normal/session_1_scenario_1_bias_neg100.json", "Cheater (Bias -100)", "red"),
#     ("Wifi7_Datasets/Normal/session_1_scenario_1_bias_neg500.json", "Cheater (Bias -500)", "red"),
#     ("Wifi7_Datasets/Normal/session_1_scenario_1_bias_neg1000.json", "Cheater (Bias -1000)", "red"),
#     ("Wifi7_Datasets/Normal/session_1_scenario_1_bias_neg5000.json", "Cheater (Bias -5000)", "red"),
# ]

# # Set this to the folder containing your files. 
# # Use "." if files are in the same folder as this script.
# BASE_DIR = "." 

# # ==========================================
# # 2. DATA LOADING ENGINE
# # ==========================================
# def load_datasets(dataset_config, base_dir):
#     loaded_dfs = []
#     colors_map = {}
    
#     print(f"Scanning directory: {os.path.abspath(base_dir)}")
    
#     for filename, label, color in dataset_config:
#         filepath = os.path.join(base_dir, filename)
        
#         if not os.path.exists(filepath):
#             print(f"⚠️ Warning: File not found: {filename} (Skipping)")
#             continue
            
#         try:
#             with open(filepath, 'r') as f:
#                 data = json.load(f)
                
#             df = pd.DataFrame(data)
            
#             # Basic Validation
#             if df.empty:
#                 print(f"⚠️ Warning: File is empty: {filename}")
#                 continue
                
#             # Add metadata for plotting
#             df['Scenario'] = label
#             # Convert window count to Seconds (assuming 0.1s per window)
#             if 'window' in df.columns:
#                 df['Time (s)'] = df['window'] * 0.1
#             else:
#                 df['Time (s)'] = df.index  # Fallback if window is missing
                
#             loaded_dfs.append(df)
#             colors_map[label] = color
#             print(f"✅ Loaded: {label} ({len(df)} rows)")
            
#         except Exception as e:
#             print(f"❌ Error loading {filename}: {e}")
            
#     return loaded_dfs, colors_map

# # ==========================================
# # 3. DYNAMIC PLOTTING ENGINE
# # ==========================================
# def plot_comparison(dfs, color_map):
#     if not dfs:
#         print("No data to plot.")
#         return

#     # Combine all data to find common columns
#     df_final = pd.concat(dfs, ignore_index=True)
    
#     # 1. Identify Metric Columns (Exclude metadata)
#     exclude_cols = ['window', 'bias', 'Scenario', 'Time (s)']
    
#     # Select only numeric columns that are NOT in the exclude list
#     metric_cols = [
#         c for c in df_final.columns 
#         if c not in exclude_cols and pd.api.types.is_numeric_dtype(df_final[c])
#     ]
    
#     print(f"\n📊 plotting {len(metric_cols)} parameters...")

#     # 2. Calculate Grid Layout
#     num_plots = len(metric_cols)
#     cols = 3
#     rows = math.ceil(num_plots / cols)
    
#     # 3. Setup Plot
#     plt.style.use('seaborn-v0_8-whitegrid') # A nice clean style
#     fig, axes = plt.subplots(rows, cols, figsize=(18, 4 * rows))
#     fig.suptitle('WiFi 7 Multi-Dataset Comparison', fontsize=20, weight='bold', y=0.98)
    
#     # Flatten axes array for easy iteration
#     if num_plots > 1:
#         axes_flat = axes.flatten()
#     else:
#         axes_flat = [axes] # Handle case of single plot

#     # 4. Loop through every metric
#     for i, metric in enumerate(metric_cols):
#         ax = axes_flat[i]
        
#         # Determine if we need Log Scale (for huge backoff numbers)
#         # We check the max value across ALL datasets for this metric
#         max_val = df_final[metric].max()
#         use_log = False
#         if "backoff" in metric.lower() and max_val > 10000:
#             use_log = True
        
#         # Plot each scenario
#         for label, color in color_map.items():
#             subset = df_final[df_final['Scenario'] == label]
#             if not subset.empty:
#                 ax.plot(subset["Time (s)"], subset[metric], 
#                         label=label, color=color, alpha=0.8, linewidth=1.5)
        
#         # Styling the subplot
#         ax.set_title(metric, fontsize=11, weight='bold')
#         ax.grid(True, linestyle='--', alpha=0.6)
        
#         # Apply Log Scale if needed
#         if use_log:
#             ax.set_yscale('symlog') # symlog handles 0 better than standard log
#             ax.set_ylabel("Log Scale")
        
#         # Formatting specifics
#         if "ratio" in metric.lower():
#             ax.set_ylim(-0.05, 1.05) # Keep ratios between 0 and 1
            
#         # Only put legend on the first plot to avoid clutter, 
#         # or put it on all if you prefer. Here we put it on the first one.
#         if i == 0:
#             ax.legend(fontsize=9, loc='upper right', frameon=True)

#     # 5. Cleanup empty subplots
#     for j in range(num_plots, len(axes_flat)):
#         fig.delaxes(axes_flat[j])

#     plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    
#     # Save and Show
#     output_filename = "multi_dataset_comparison.png"
#     plt.savefig(output_filename, dpi=300)
#     print(f"\n💾 Graph saved to: {output_filename}")
#     plt.show()

# # ==========================================
# # 4. RUNNER
# # ==========================================
# # Load
# dfs, colors = load_datasets(DATASETS, BASE_DIR)
# # Plot
# plot_comparison(dfs, colors)




























import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import pandas as pd
import matplotlib.pyplot as plt
import math
import os
import numpy as np  # Added for safe type checking

# ==========================================
# BACKEND LOGIC
# ==========================================
def load_and_parse_files(file_paths):
    dfs = []
    found_metrics = set()
    
    for filepath in file_paths:
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            
            if df.empty: continue
            
            # Auto-generate a label from the filename
            filename = os.path.basename(filepath)
            
            # Smart Labeling Logic
            if "bias_0" in filename or "Normal" in filename or "apple_0" in filename:
                label = f"Normal (Bias 0) - {filename}"
            elif "neg" in filename:
                try:
                    bias = filename.split("neg")[-1].split(".")[0]
                    label = f"Cheater (Bias -{bias})"
                except:
                    label = f"Cheater - {filename}"
            elif "bias" in filename:
                try:
                    bias = filename.split("bias_")[-1].split(".")[0]
                    label = f"Attack (Bias {bias})"
                except:
                    label = f"Attack - {filename}"
            else:
                label = filename.replace(".json", "")
                
            df['Scenario'] = label
            
            # Time conversion
            if 'window' in df.columns:
                df['Time (s)'] = df['window'] * 0.1
            else:
                df['Time (s)'] = df.index

            dfs.append(df)
            
            # Collect metrics (exclude metadata)
            exclude = ['window', 'bias', 'Scenario', 'Time (s)']
            for col in df.columns:
                if col not in exclude and pd.api.types.is_numeric_dtype(df[col]):
                    found_metrics.add(col)
                    
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            
    return dfs, sorted(list(found_metrics))

def generate_plot(dfs, selected_metrics):
    if not dfs or not selected_metrics:
        return

    df_final = pd.concat(dfs, ignore_index=True)
    
    num_plots = len(selected_metrics)
    
    # --- FIX: DYNAMIC GRID CALCULATION ---
    # Only use 3 columns if we have 3 or more plots. 
    # Otherwise use num_plots (e.g., 1 plot = 1 column).
    cols = min(3, num_plots)
    rows = math.ceil(num_plots / cols)
    
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Adjust figure size based on columns
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 4 * rows))
    fig.suptitle('WiFi 7 Dataset Analysis', fontsize=20, weight='bold', y=0.98)
    
    # --- FIX: ROBUST FLATTENING ---
    # subplots returns an Array if multiple plots, or a single Object if 1 plot.
    # We strictly check if it's an array to flatten it.
    if hasattr(axes, "flatten"):
        axes_flat = axes.flatten()
    else:
        axes_flat = [axes]

    # Assign colors automatically
    unique_scenarios = df_final['Scenario'].unique()
    colors = plt.cm.tab10(range(len(unique_scenarios)))
    color_map = {name: color for name, color in zip(unique_scenarios, colors)}

    for i, metric in enumerate(selected_metrics):
        ax = axes_flat[i]
        
        # Log scale check
        max_val = df_final[metric].max()
        use_log = False
        if "backoff" in metric.lower() and max_val > 10000:
            use_log = True
        
        for label in unique_scenarios:
            subset = df_final[df_final['Scenario'] == label]
            if not subset.empty:
                ax.plot(subset["Time (s)"], subset[metric], 
                        label=label, color=color_map[label], alpha=0.8, linewidth=1.5)
        
        ax.set_title(metric, fontsize=10, weight='bold')
        ax.grid(True, linestyle='--', alpha=0.6)
        
        if use_log:
            ax.set_yscale('symlog')
            ax.set_ylabel("Log Scale")
        if "ratio" in metric.lower():
            ax.set_ylim(-0.05, 1.05)
            
        # Legend on the first plot
        if i == 0:
            ax.legend(fontsize=8, loc='upper right')

    # Remove empty subplots
    for j in range(num_plots, len(axes_flat)):
        fig.delaxes(axes_flat[j])

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    plt.show()

# ==========================================
# GUI FRONTEND
# ==========================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("WiFi 7 Data Visualizer")
        self.root.geometry("600x700")
        
        self.loaded_dfs = []
        self.available_metrics = []
        self.metric_vars = {} 

        # --- Section 1: File Selection ---
        frame_files = tk.LabelFrame(root, text="1. Select Datasets", padx=10, pady=10)
        frame_files.pack(fill="x", padx=10, pady=5)
        
        btn_add = tk.Button(frame_files, text="📂 Add JSON Files", command=self.add_files, bg="#dddddd")
        btn_add.pack(anchor="w")
        
        self.listbox = tk.Listbox(frame_files, height=6)
        self.listbox.pack(fill="x", pady=5)
        
        # FIXED: Removed 'text_color' arg that caused the first error
        btn_clear = tk.Button(frame_files, text="Clear List", command=self.clear_files, fg="red")
        btn_clear.pack(anchor="e")

        # --- Section 2: Metric Selection ---
        frame_metrics = tk.LabelFrame(root, text="2. Select Parameters to Plot", padx=10, pady=10)
        frame_metrics.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Scrollable Frame
        canvas = tk.Canvas(frame_metrics)
        scrollbar = tk.Scrollbar(frame_metrics, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        frame_btns = tk.Frame(frame_metrics)
        frame_btns.pack(side="bottom", fill="x", pady=5)
        tk.Button(frame_btns, text="Select All", command=self.select_all).pack(side="left")
        tk.Button(frame_btns, text="Deselect All", command=self.deselect_all).pack(side="left", padx=5)

        # --- Section 3: Action ---
        btn_plot = tk.Button(root, text="📊 GENERATE GRAPHS", command=self.on_plot, 
                             bg="green", fg="white", font=("Arial", 12, "bold"), height=2)
        btn_plot.pack(fill="x", padx=20, pady=20)

    def add_files(self):
        filepaths = filedialog.askopenfilenames(filetypes=[("JSON Files", "*.json")])
        if filepaths:
            for fp in filepaths:
                self.listbox.insert(tk.END, os.path.basename(fp))
            
            new_dfs, metrics = load_and_parse_files(filepaths)
            self.loaded_dfs.extend(new_dfs)
            
            current_metrics = set(self.available_metrics)
            new_metrics_set = set(metrics)
            
            if not new_metrics_set.issubset(current_metrics):
                self.available_metrics = sorted(list(current_metrics.union(new_metrics_set)))
                self.refresh_checkboxes()

    def clear_files(self):
        self.listbox.delete(0, tk.END)
        self.loaded_dfs = []
        self.available_metrics = []
        self.refresh_checkboxes()

    def refresh_checkboxes(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.metric_vars = {}

        for metric in self.available_metrics:
            var = tk.IntVar(value=1)
            chk = tk.Checkbutton(self.scrollable_frame, text=metric, variable=var, anchor="w")
            chk.pack(fill="x")
            self.metric_vars[metric] = var

    def select_all(self):
        for var in self.metric_vars.values(): var.set(1)

    def deselect_all(self):
        for var in self.metric_vars.values(): var.set(0)

    def on_plot(self):
        if not self.loaded_dfs:
            messagebox.showwarning("No Data", "Please select at least one JSON file first.")
            return
        
        selected = [m for m, var in self.metric_vars.items() if var.get() == 1]
        
        if not selected:
            messagebox.showwarning("No Metrics", "Please select at least one parameter to plot.")
            return
            
        generate_plot(self.loaded_dfs, selected)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()