# import json
# import requests
# import time
# from pathlib import Path

# # Configuration
# API_URL = "http://127.0.0.1:8500/predict"  # Use 127.0.0.1 instead of 0.0.0.0 for client scripts
# INPUT_FILE = "../attack/All the data.json"  # Change to your file path
# OUTPUT_FILE = "detected_attacks.json"
# THRESHOLD = 0.3
# GRAPH_LEN = 32

# def test_stream():
#     # 1. Load the Data
#     print(f"📂 Loading data from {INPUT_FILE}...")
#     try:
#         with open(INPUT_FILE, "r") as f:
#             all_windows = json.load(f)
#     except FileNotFoundError:
#         print("❌ Error: Input file not found.")
#         return

#     total_records = len(all_windows)
#     print(f"   Loaded {total_records} records.")

#     if total_records < GRAPH_LEN:
#         print(f"❌ Error: Not enough data. Need at least {GRAPH_LEN} rows.")
#         return

#     # Prepare output list
#     detected_attacks = []

#     # 2. Simulate Streaming (Sliding Window)
#     # We start from index 32 so we always have enough history to send
#     print(f"🚀 Starting stream to {API_URL}...")

#     for i in range(GRAPH_LEN, total_records + 1):
#         # Slice the last 32 windows (indices i-32 to i)
#         # This mimics the "Live" buffer the GNN needs
#         current_batch = all_windows[i - GRAPH_LEN : i]

#         # The specific row we are testing is the LAST one in the batch
#         current_row = current_batch[-1]

#         payload = {
#             "experiment_id": "test_script_v1",
#             "windows": current_batch
#         }

#         try:
#             # Send POST request
#             response = requests.post(API_URL, json=payload)

#             if response.status_code == 200:
#                 result = response.json()
#                 prob = result["attack_probability"]

#                 # Check Threshold
#                 if prob > THRESHOLD:
#                     print(f"⚠️  [Row {i}] DETECTED! Prob: {prob:.4f}")
#                     detected_attacks.append(current_row)
#                 else:
#                     # Optional: Print normal dots to show progress
#                     if i % 10 == 0: print(".", end="", flush=True)
#             else:
#                 print(f"\n❌ API Error {response.status_code}: {response.text}")
#                 break

#         except requests.exceptions.ConnectionError:
#             print("\n❌ Connection Error: Is the API running? (uvicorn GNN.service.main:app)")
#             break

#     # 3. Save Results
#     print(f"\n\n🏁 Done. Found {len(detected_attacks)} attack rows.")

#     if detected_attacks:
#         with open(OUTPUT_FILE, "w") as out:
#             json.dump(detected_attacks, out, indent=2)
#         print(f"💾 Saved attack rows to: {OUTPUT_FILE}")
#     else:
#         print("✅ No attacks detected above threshold.")

# if __name__ == "__main__":
#     test_stream()


# import json
# import requests
# import sys
# import glob
# from pathlib import Path

# # --- Configuration ---
# API_URL = "http://127.0.0.1:8500/predict"
# INPUT_PATTERN = "/home/pathum/FYP Project/my-gnn-code/data/attack/*.json"
# OUTPUT_FILE = "detected_events.json"
# GRAPH_LEN = 32

# CLASS_NAMES = {
#     0: "🟢 NORMAL",
#     1: "🔴 POSITIVE ATTACK",
#     2: "🟠 NEGATIVE ATTACK"
# }

# def test_stream_all():
#     files = sorted(glob.glob(INPUT_PATTERN))

#     if not files:
#         print(f"❌ No files found matching: {INPUT_PATTERN}")
#         return

#     print(f"Found {len(files)} files to process.\n")

#     all_detected_events = []

#     print(f"{'FILE':<25} | {'ROW ID':<8} | {'PREDICTED CLASS':<20} | {'PROBABILITIES':<30}")
#     print("-" * 90)

#     for file_path in files:
#         file_name = Path(file_path).name

#         try:
#             with open(file_path, "r") as f:
#                 all_windows = json.load(f)
#         except Exception as e:
#             print(f"❌ Error reading {file_name}: {e}")
#             continue

#         total_records = len(all_windows)

#         if total_records < GRAPH_LEN:
#             print(f"{file_name:<25} | SKIPPED (Too short, len={total_records})")
#             continue

#         for i in range(GRAPH_LEN, total_records + 1):
#             current_batch = all_windows[i - GRAPH_LEN : i]
#             current_row = current_batch[-1]

#             payload = {
#                 "experiment_id": "test_script_3_class",
#                 "windows": current_batch
#             }

#             try:
#                 response = requests.post(API_URL, json=payload)

#                 if response.status_code == 200:
#                     result = response.json()
#                     pred_class = result["predicted_class"]
#                     probs = result["probabilities"]

#                     verdict = CLASS_NAMES.get(pred_class, "UNKNOWN")

#                     # Format probabilities for printing
#                     probs_str = ", ".join([f"{p:.2f}" for p in probs])

#                     display_name = (file_name[:22] + '..') if len(file_name) > 22 else file_name
#                     print(f"{display_name:<25} | {i:<8} | {verdict:<20} | {probs_str}")

#                     # Save if not normal
#                     if pred_class != 0:
#                         current_row['_source_file'] = file_name
#                         current_row['_predicted_class'] = verdict
#                         all_detected_events.append(current_row)

#                 else:
#                     print(f"❌ API Error: {response.status_code} - {response.text}")
#                     break

#             except requests.exceptions.ConnectionError:
#                 print(f"\n❌ Connection Refused! Is the API running?")
#                 sys.exit(1)

#         print("-" * 90)

#     print(f"\n🏁 Finished processing {len(files)} files.")
#     print(f"📊 Total Non-Normal Events Detected: {len(all_detected_events)}")

#     if all_detected_events:
#         with open(OUTPUT_FILE, "w") as out:
#             json.dump(all_detected_events, out, indent=2)
#         print(f"💾 All detected non-normal event rows saved to: {OUTPUT_FILE}")

# if __name__ == "__main__":
#     test_stream_all()

#

# import json
# import requests
# import sys
# import glob
# import re
# from pathlib import Path
# from sklearn.metrics import confusion_matrix, classification_report, accuracy_score

# # --- Configuration ---
# API_URL = "http://127.0.0.1:8500/predict"
# NORMAL_PATTERN = "data/test/normal/*.json"
# ATTACK_PATTERN = "data/test/attack/*.json"
# OUTPUT_FILE = "detected_events.json"
# GRAPH_LEN = 32

# # Class definitions
# CLASS_NAMES = {
#     0: "🟢 NORMAL",
#     1: "🔴 ATTACK",
#     2: "🟠 NEGATIVE ATTACK"
# }

# def get_label_from_filename(path):
#     path_str = str(path).lower()
#     if "normal" in path_str:
#         return 0
#     filename = Path(path).name
#     match = re.search(r'bias_([a-zA-Z]*)?(\d+)', filename)
#     if match:
#         return 2 if match.group(1) == "neg" else 1
#     return 1

# def test_stream_all():
#     normal_files = sorted(glob.glob(NORMAL_PATTERN))
#     attack_files = sorted(glob.glob(ATTACK_PATTERN))
#     all_files = normal_files + attack_files

#     if not all_files:
#         print(f"❌ No files found.")
#         return

#     print(f"Found {len(all_files)} files. Processing all data points...\n")

#     all_detected_events = []

#     # Lists to store ground truth vs predictions
#     y_true_all = []
#     y_pred_all = []

#     # Header
#     print(f"{'FILE':<25} | {'ROW':<5} | {'TRUE':<10} | {'PRED':<10} | {'CONF':<6} | {'STATUS'}")
#     print("-" * 90)

#     for file_path in all_files:
#         file_name = Path(file_path).name
#         true_label = get_label_from_filename(file_path)
#         true_name = CLASS_NAMES.get(true_label, "UNKNOWN")

#         try:
#             with open(file_path, "r") as f:
#                 all_windows = json.load(f)
#         except Exception:
#             continue

#         total_records = len(all_windows)
#         if total_records < GRAPH_LEN:
#             continue

#         # Process EVERY window
#         for i in range(GRAPH_LEN, total_records + 1):
#             current_batch = all_windows[i - GRAPH_LEN : i]
#             current_row = current_batch[-1]

#             payload = {
#                 "experiment_id": "full_metrics_test",
#                 "windows": current_batch
#             }

#             try:
#                 response = requests.post(API_URL, json=payload)

#                 if response.status_code == 200:
#                     result = response.json()

#                     # Logic to handle Binary Server Response
#                     if "attack_probability" in result:
#                         prob = result["attack_probability"]
#                         if prob > 0.5:
#                             pred_class = 1
#                             confidence = prob
#                         else:
#                             pred_class = 0
#                             confidence = 1.0 - prob
#                     elif "predicted_class" in result:
#                         pred_class = result["predicted_class"]
#                         confidence = 1.0
#                     else:
#                         continue

#                     pred_name = "NORMAL" if pred_class == 0 else "ATTACK"

#                     # Store for final metrics
#                     y_true_all.append(true_label)
#                     y_pred_all.append(pred_class)

#                     # Visual feedback (only print errors or every 100th row to save space)
#                     is_correct = (true_label == pred_class)
#                     if not is_correct or i % 100 == 0:
#                         status_icon = "✅" if is_correct else "❌"
#                         display_name = (file_name[:20] + '..') if len(file_name) > 20 else file_name
#                         print(f"{display_name:<25} | {i:<5} | {true_name:<10} | {pred_name:<10} | {confidence:.2f}   | {status_icon}")

#                     if pred_class != 0:
#                         current_row['_source_file'] = file_name
#                         current_row['_prob'] = confidence
#                         all_detected_events.append(current_row)

#                 else:
#                     print(f"❌ API Error: {response.status_code}")
#                     break

#             except requests.exceptions.ConnectionError:
#                 sys.exit(1)

#     print("-" * 90)
#     print("\nProcessing Complete. Generating Metrics...\n")

#     if len(y_true_all) > 0:
#         # 1. Classification Report (Precision, Recall, F1)
#         print("=== CLASSIFICATION REPORT ===")
#         print(classification_report(y_true_all, y_pred_all, target_names=["NORMAL", "ATTACK", "NEGATIVE ATTACK"], digits=4))

#         # 2. Confusion Matrix
#         cm = confusion_matrix(y_true_all, y_pred_all)

#         print("=== CONFUSION MATRIX ===")
#         print(f"                 Predicted Normal   Predicted Attack  Predicted Negative")
#         print(f"Actual Normal      {cm[0][0]:<18} {cm[0][1]:<18} {cm[0][2]:<18}")
#         print(f"Actual Attack      {cm[1][0]:<18} {cm[1][1]:<18} {cm[1][2]:<18}")
#         print(f"Actual Negative    {cm[2][0]:<18} {cm[2][1]:<18} {cm[2][2]:<18}")
#         print("-" * 40)
#         print(f"Total Samples: {len(y_true_all)}")
#         print(f"Accuracy:      {accuracy_score(y_true_all, y_pred_all):.4%}")

#     # Save details
#     if all_detected_events:
#         with open(OUTPUT_FILE, "w") as out:
#             json.dump(all_detected_events, out, indent=2)
#         print(f"\n💾 Saved {len(all_detected_events)} detected events to: {OUTPUT_FILE}")

# if __name__ == "__main__":
#     test_stream_all()


import json
import requests
import sys
import glob
import re
from pathlib import Path
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
import sys
sys.stdout.reconfigure(encoding="utf-8")

# --- Configuration ---
API_URL = "http://127.0.0.1:8000/predict"
NORMAL_PATTERN = "data/test/normal/*.json"  # data\test\attack
ATTACK_PATTERN = "data/test/attack/*.json"
# NORMAL_PATTERN = "data/normal/*.json"
# ATTACK_PATTERN = "data/attack/*.json"
OUTPUT_FILE = "detected_events.json"
GRAPH_LEN = 32

# Class definitions (Simplified to Binary)
CLASS_NAMES = {
    0: "🟢 NORMAL",
    1: "🔴 ATTACK"
}


def get_label_from_filename(path):
    """
    Returns 0 for Normal, 1 for ANY Attack (Positive or Negative).
    """
    path_str = str(path).lower()
    if "normal" in path_str:
        return 0
    # If it's not normal, we assume it is an attack (Class 1)
    return 1


def test_stream_all():
    normal_files = sorted(glob.glob(NORMAL_PATTERN))
    attack_files = sorted(glob.glob(ATTACK_PATTERN))
    all_files = normal_files + attack_files

    if not all_files:
        print(f"❌ No files found. Please check paths:")
        print(f"   - {NORMAL_PATTERN}")
        print(f"   - {ATTACK_PATTERN}")
        return

    print(f"Found {len(all_files)} files. Processing all data points...\n")

    all_detected_events = []

    # Lists to store ground truth vs predictions
    y_true_all = []
    y_pred_all = []

    # Header
    print(f"{'FILE':<25} | {'ROW':<5} | {'TRUE':<10} | {'PRED':<10} | {'CONF':<6} | {'STATUS'}")
    print("-" * 90)

    for file_path in all_files:
        file_name = Path(file_path).name
        true_label = get_label_from_filename(
            file_path)  # Now returns only 0 or 1
        true_name = CLASS_NAMES.get(true_label, "UNKNOWN")

        try:
            with open(file_path, "r") as f:
                all_windows = json.load(f)
        except Exception:
            continue

        total_records = len(all_windows)
        if total_records < GRAPH_LEN:
            continue

        # Process EVERY window
        for i in range(GRAPH_LEN, total_records + 1):
            current_batch = all_windows[i - GRAPH_LEN: i]
            current_row = current_batch[-1]

            payload = {
                "experiment_id": "full_metrics_test",
                "windows": current_batch
            }

            try:
                response = requests.post(API_URL, json=payload)

                if response.status_code == 200:
                    result = response.json()

                    # --- BINARY MAPPING LOGIC ---
                    if "attack_probability" in result:
                        prob = result["attack_probability"]
                        if prob > 0.3:
                            pred_class = 1
                            confidence = prob
                        else:
                            pred_class = 0
                            confidence = 1.0 - prob

                    elif "predicted_class" in result:
                        raw_pred = result["predicted_class"]
                        # FORCE MAPPING: If model predicts 2 (Negative), treat as 1 (Attack)
                        if raw_pred == 2:
                            pred_class = 1
                        else:
                            pred_class = raw_pred
                        confidence = 1.0
                    else:
                        continue
                    # ----------------------------

                    pred_name = "NORMAL" if pred_class == 0 else "ATTACK"

                    # Store for final metrics
                    y_true_all.append(true_label)
                    y_pred_all.append(pred_class)

                    # Visual feedback (only print errors or every 100th row)
                    is_correct = (true_label == pred_class)
                    if not is_correct or i % 100 == 0:
                        status_icon = "✅" if is_correct else "❌"
                        display_name = (
                            file_name[:20] + '..') if len(file_name) > 20 else file_name
                        print(
                            f"{display_name:<25} | {i:<5} | {true_name:<10} | {pred_name:<10} | {confidence:.2f}   | {status_icon}")

                    # If it's an attack, save the event
                    if pred_class != 0:
                        current_row['_source_file'] = file_name
                        current_row['_prob'] = confidence
                        all_detected_events.append(current_row)

                else:
                    print(f"❌ API Error: {response.status_code}")
                    break

            except requests.exceptions.ConnectionError:
                print("❌ Connection failed. Ensure the server is running.")
                sys.exit(1)

    print("-" * 90)
    print("\nProcessing Complete. Generating Metrics...\n")

    if len(y_true_all) > 0:
        # 1. Classification Report (Now Binary)
        print("=== CLASSIFICATION REPORT ===")
        print(classification_report(y_true_all, y_pred_all,
              target_names=["NORMAL", "ATTACK"], digits=4))

        # 2. Confusion Matrix (Now 2x2)
        cm = confusion_matrix(y_true_all, y_pred_all)

        # Handle case where confusion matrix might not be 2x2 if only one class was present
        tn, fp, fn, tp = 0, 0, 0, 0
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
        elif cm.shape == (1, 1):
            # If only one class exists in the data (e.g., only Normal files were processed)
            if y_true_all[0] == 0:
                tn = cm[0, 0]
            else:
                tp = cm[0, 0]

        print("=== CONFUSION MATRIX ===")
        print(f"                 Predicted Normal   Predicted Attack")
        print(f"Actual Normal      {tn:<18} {fp:<18}")
        print(f"Actual Attack      {fn:<18} {tp:<18}")
        print("-" * 40)
        print(f"Total Samples: {len(y_true_all)}")
        print(f"Accuracy:      {accuracy_score(y_true_all, y_pred_all):.4%}")

    # Save details
    if all_detected_events:
        with open(OUTPUT_FILE, "w") as out:
            json.dump(all_detected_events, out, indent=2)
        print(
            f"\n💾 Saved {len(all_detected_events)} detected events to: {OUTPUT_FILE}")


if __name__ == "__main__":
    test_stream_all()
