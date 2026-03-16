"""
Evaluation metrics for WiFi 7 attack detection.

This module provides comprehensive metrics for binary classification,
with emphasis on security-relevant metrics (recall, precision, F1).
"""

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns


def compute_class_weights(labels: List[int]) -> torch.Tensor:
    """
    Compute class weights for imbalanced dataset.

    Uses inverse frequency weighting: more weight to minority class.

    Args:
        labels: List of binary labels (0 or 1)

    Returns:
        Class weights tensor [2]

    Example:
        >>> labels = [0, 0, 0, 1]  # 3 normal, 1 attack
        >>> weights = compute_class_weights(labels)
        >>> weights
        tensor([0.6667, 2.0000])  # Attack class has higher weight
    """
    labels_np = np.array(labels)
    class_counts = np.bincount(labels_np)
    total = len(labels)

    # Inverse frequency weighting
    weights = total / (len(class_counts) * class_counts)

    return torch.tensor(weights, dtype=torch.float)


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_probs: np.ndarray = None
) -> Dict[str, float]:
    """
    Compute comprehensive evaluation metrics.

    Args:
        y_true: True labels [N]
        y_pred: Predicted labels [N]
        y_probs: Predicted probabilities [N] (optional, for ROC-AUC)

    Returns:
        Dictionary with metrics:
        - accuracy: Overall accuracy
        - precision: Precision (TP / (TP + FP))
        - recall: Recall (TP / (TP + FN)) - Most important for security!
        - f1: F1 score (harmonic mean of precision and recall)
        - auc: ROC-AUC score (if probabilities provided)
        - confusion_matrix: 2x2 confusion matrix

    Example:
        >>> y_true = np.array([0, 0, 1, 1])
        >>> y_pred = np.array([0, 1, 1, 1])
        >>> metrics = compute_metrics(y_true, y_pred)
        >>> metrics['f1']
        0.8
    """
    metrics = {}

    # Basic metrics
    metrics['accuracy'] = accuracy_score(y_true, y_pred)
    metrics['precision'] = precision_score(y_true, y_pred, average='binary', zero_division=0)
    metrics['recall'] = recall_score(y_true, y_pred, average='binary', zero_division=0)
    metrics['f1'] = f1_score(y_true, y_pred, average='binary', zero_division=0)

    # ROC-AUC (if probabilities provided)
    if y_probs is not None:
        try:
            metrics['auc'] = roc_auc_score(y_true, y_probs)
        except ValueError:
            # Only one class present in y_true
            metrics['auc'] = 0.0
    else:
        metrics['auc'] = 0.0

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    metrics['confusion_matrix'] = cm

    # Compute FP, FN, TP, TN from confusion matrix
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        metrics['true_negatives'] = int(tn)
        metrics['false_positives'] = int(fp)
        metrics['false_negatives'] = int(fn)
        metrics['true_positives'] = int(tp)

        # False positive rate and false negative rate
        metrics['fpr'] = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        metrics['fnr'] = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    return metrics


def print_metrics(metrics: Dict, prefix: str = ""):
    """
    Print metrics in a formatted way.

    Args:
        metrics: Dictionary of metrics
        prefix: Prefix for printing (e.g., "Train", "Val", "Test")
    """
    print(f"\n{'='*60}")
    print(f"{prefix} METRICS")
    print(f"{'='*60}")
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f} ← Most important for attack detection")
    print(f"F1 Score:  {metrics['f1']:.4f}")
    print(f"ROC-AUC:   {metrics['auc']:.4f}")

    if 'confusion_matrix' in metrics:
        print(f"\nConfusion Matrix:")
        print(metrics['confusion_matrix'])
        print("\n[[TN  FP]")
        print(" [FN  TP]]")

        if 'fpr' in metrics and 'fnr' in metrics:
            print(f"\nFalse Positive Rate: {metrics['fpr']:.4f}")
            print(f"False Negative Rate: {metrics['fnr']:.4f} ← Missed attacks")

    print(f"{'='*60}")


def plot_confusion_matrix(
    cm: np.ndarray,
    save_path: str = None,
    title: str = "Confusion Matrix"
):
    """
    Plot confusion matrix as a heatmap.

    Args:
        cm: Confusion matrix [2, 2]
        save_path: Path to save the plot (optional)
        title: Plot title
    """
    plt.figure(figsize=(8, 6))

    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=['Normal', 'Attack'],
        yticklabels=['Normal', 'Attack'],
        cbar_kws={'label': 'Count'}
    )

    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.title(title)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Confusion matrix saved to {save_path}")

    plt.close()


def plot_training_history(
    train_losses: List[float],
    val_metrics: List[Dict],
    save_path: str = None
):
    """
    Plot training history (loss and metrics over epochs).

    Args:
        train_losses: List of training losses per epoch
        val_metrics: List of validation metrics dictionaries per epoch
        save_path: Path to save the plot (optional)
    """
    epochs = range(1, len(train_losses) + 1)

    # Extract validation metrics
    val_f1 = [m['f1'] for m in val_metrics]
    val_acc = [m['accuracy'] for m in val_metrics]
    val_auc = [m['auc'] for m in val_metrics]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Training Loss
    axes[0, 0].plot(epochs, train_losses, 'b-', label='Train Loss')
    axes[0, 0].set_xlabel('Epoch')
    axes[0, 0].set_ylabel('Loss')
    axes[0, 0].set_title('Training Loss')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].legend()

    # Plot 2: Validation F1
    axes[0, 1].plot(epochs, val_f1, 'g-', label='Val F1')
    axes[0, 1].set_xlabel('Epoch')
    axes[0, 1].set_ylabel('F1 Score')
    axes[0, 1].set_title('Validation F1 Score')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].legend()

    # Plot 3: Validation Accuracy
    axes[1, 0].plot(epochs, val_acc, 'r-', label='Val Accuracy')
    axes[1, 0].set_xlabel('Epoch')
    axes[1, 0].set_ylabel('Accuracy')
    axes[1, 0].set_title('Validation Accuracy')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].legend()

    # Plot 4: Validation AUC
    axes[1, 1].plot(epochs, val_auc, 'purple', label='Val AUC')
    axes[1, 1].set_xlabel('Epoch')
    axes[1, 1].set_ylabel('ROC-AUC')
    axes[1, 1].set_title('Validation ROC-AUC')
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].legend()

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Training history saved to {save_path}")

    plt.close()


def evaluate_model(model, loader, device):
    """
    Evaluate model on a dataset.

    Args:
        model: PyTorch model
        loader: DataLoader
        device: Device to run evaluation on

    Returns:
        Dictionary with metrics
    """
    model.eval()

    all_preds = []
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for data in loader:
            data = data.to(device)

            # Forward pass
            out = model(data.x, data.edge_index, data.batch)

            # Get predictions and probabilities
            probs = torch.softmax(out, dim=1)
            preds = out.argmax(dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(data.y.cpu().numpy())
            all_probs.extend(probs[:, 1].cpu().numpy())  # Probability of attack class

    # Compute metrics
    metrics = compute_metrics(
        np.array(all_labels),
        np.array(all_preds),
        np.array(all_probs)
    )

    return metrics


if __name__ == "__main__":
    # Test metrics module
    print("Testing metrics module...")
    print()

    # Test data
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
    y_pred = np.array([0, 0, 1, 0, 1, 1, 0, 1, 1, 1])
    y_probs = np.array([0.1, 0.2, 0.6, 0.3, 0.8, 0.9, 0.4, 0.7, 0.85, 0.95])

    # Compute metrics
    metrics = compute_metrics(y_true, y_pred, y_probs)
    print_metrics(metrics, prefix="Test")

    # Test class weights
    print("\nClass Weights:")
    weights = compute_class_weights(y_true.tolist())
    print(f"  Class 0 (Normal): {weights[0]:.4f}")
    print(f"  Class 1 (Attack): {weights[1]:.4f}")

    print("\n✓ Metrics module working correctly!")
