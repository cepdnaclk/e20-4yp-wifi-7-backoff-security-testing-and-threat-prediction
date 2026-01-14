# Modeling Guide: Replicating the GNN Project

This guide provides a step-by-step walkthrough for setting up, training, and evaluating the GNN attack detection model. It is intended for developers or researchers looking to replicate this work or use it as a foundation for their own projects.

## 1. Environment Setup

Before you begin, ensure you have a Python environment with the following key libraries installed:

-   `torch` (PyTorch)
-   `scikit-learn`
-   `numpy`

You can typically install them using pip:
`pip install torch scikit-learn numpy`

## 2. Data Preparation

The model expects data to be in a specific format.

-   **Input Format:** The `BackoffDataset` class is designed to load data from a directory of `.json` files. Each JSON file should represent one graph instance (i.e., one sequence of events).
-   **File Contents:** Each JSON file must contain the raw data needed to construct the following:
    -   An adjacency matrix `A` (or the raw connections to build one).
    -   The raw window/event data that the `feature_engineering` function can convert into the 14-dimensional feature vectors (`X`).
    -   A `label` (0 for normal, 1 for positive attack, 2 for negative attack).
-   **Directory Structure:** Place all your training data JSON files in one directory and your testing data JSON files in another. The `train_attack.py` and `eval.py` scripts take these directory paths as command-line arguments.

## 3. The Modeling Pipeline

The process is divided into two main stages: training and evaluation.

### Step 3.1: Training the Model

The `train_attack.py` script handles the training process.

-   **Execution:** You run the script from the command line, providing paths to your training data and where you want to save the trained model.
-   **Command:**
    ```bash
    python GNN/train_attack.py --data_dir /path/to/your/training/data --artifact_path /path/to/save/model.pt
    ```
-   **Process:**
    1.  The script initializes the `BackoffDataset` to load the training data.
    2.  It creates an instance of the `AttackGCN` model defined in `GNN/attack_model.py`.
    3.  It runs the training loop for a specified number of epochs (this can be added as a command-line argument). In each epoch, it feeds batches of data (graphs) to the model, calculates the loss, and updates the model's weights using the Adam optimizer.
    4.  After training is complete, it saves the learned model weights to the specified `artifact_path`.

### Step 3.2: Evaluating the Model

The `eval.py` script is used to assess the performance of the trained model on a separate test dataset.

-   **Execution:** You run this script after a model has been trained and saved.
-   **Command:**
    ```bash
    python GNN/eval.py --data_dir /path/to/your/test/data --artifact_path /path/to/your/saved/model.pt
    ```
-   **Process:**
    1.  The script loads the pre-trained model weights from the `artifact_path`.
    2.  It initializes a `BackoffDataset` to load the test data.
    3.  It iterates through the test data, making predictions for each graph.
    4.  It compares the model's predictions to the true labels and computes and prints a full classification report (accuracy, precision, recall, F1-score). This gives a clear picture of how well the model performs on unseen data.

## 4. How to Model Your Own Problem

To adapt this project for a different problem, you would primarily need to modify two areas:

1.  **`backoff_dataset.py`:**
    -   The `feature_engineering` function is the most critical part to change. You will need to design a new function that extracts meaningful features from *your* raw data to create the node feature vectors (`X`). The dimension of these vectors will also likely change.
    -   You may also need to adjust how the adjacency matrix `A` is constructed based on the relationships in your data.

2.  **`attack_model.py`:**
    -   Update the `in_dim` parameter in the `AttackGCN` constructor to match the dimension of your new feature vectors.
    -   If your problem has a different number of classes, update the `n_classes` parameter.
    -   For more complex problems, you might consider adding more GCN layers or experimenting with different types of graph pooling (e.g., max pooling).
