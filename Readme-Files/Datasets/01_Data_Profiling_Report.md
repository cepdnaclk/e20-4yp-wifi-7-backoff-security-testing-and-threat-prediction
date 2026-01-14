# Report 1: Data Profiling

## 1. Introduction

This report profiles the datasets located in the `E:\analysis\data\Data from servers\Wifi7_Datasets` directory. The purpose is to define the data's structure, format, and organization, providing a foundation for further statistical analysis.

## 2. Directory and File Structure

The data is organized in a clear, class-separated hierarchy, which is optimal for supervised machine learning tasks.

-   **Root Directory:** `Wifi7_Datasets/`
-   **Class Directories:**
    -   `Attack/`: Contains numerous JSON files, each representing a distinct attack scenario. The filenames themselves are descriptive, encoding session, scenario, bias type, and bias magnitude (e.g., `session_1_scenario_1_negative_bias_100_run_3.json`).
    -   `Normal/`: Contains JSON files representing baseline, non-attack scenarios (e.g., `session_1_scenario_1_normal_run_1.json`).

This structure provides explicit labels (`Attack` vs. `Normal`) for each data file, simplifying the data loading process for model training.

## 3. Data Format

All data files are in **JSON** format.

-   Each file contains a single JSON array.
-   Each element of the array is a JSON object that represents a single "window" or time-slice of collected metrics.
-   This structure effectively represents a time series, where the array index corresponds to the time step.

## 4. Feature Schema

Each JSON object (window) within a file contains the same set of 14 key-value pairs. All features are numerical (integer or floating-point), making them ready for direct use in quantitative analysis.

The features are:

1.  `window`: The time-slice identifier (Integer).
2.  `bias`: The bias value applied during the simulation. This is `0` for normal data and non-zero for attack data (e.g., `-100`, `500`).
3.  `net_throughput_mbps`: Network throughput in Megabits per second (Float).
4.  `net_avg_delay_ms`: Average network delay in milliseconds (Float).
5.  `net_avg_jitter_ms`: Average network jitter in milliseconds (Float).
6.  `net_packet_loss_ratio`: The ratio of lost packets (Float).
7.  `net_active_flows`: The number of active network flows (Integer).
8.  `mac_total_tx`: Total MAC layer transmissions (Integer).
9.  `mac_total_rx`: Total MAC layer receptions (Integer).
10. `mac_total_ack`: Total MAC layer acknowledgements (Integer).
11. `mac_total_retrans`: Total MAC layer retransmissions (Integer).
12. `mac_drop_count`: Number of dropped MAC layer packets (Integer).
13. `phy_drop_count`: Number of dropped Physical layer packets (Integer).
14. `avg_backoff_slots`: Average number of backoff slots (Float).
15. `channel_busy_ratio`: The ratio of time the channel was busy (Float).

## 5. Initial Observations

-   **Consistency:** The schema is consistent across all inspected files from both `Attack` and `Normal` classes.
-   **Data Quality:** There are no apparent missing values in the sampled files. All data appears to be in the correct numerical format.
-   **Labeling:** The `bias` feature serves as an explicit feature indicating an attack, while the folder structure provides a class label for the entire file.
