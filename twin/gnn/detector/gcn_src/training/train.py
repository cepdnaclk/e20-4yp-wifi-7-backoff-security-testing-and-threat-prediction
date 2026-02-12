"""
Training pipeline for WiFi 7 attack detection.

This module implements the complete training workflow:
1. Load and split files (file-level)
2. Fit scaler on training data only
3. Create datasets
4. Initialize model
5. Training loop with validation
6. Early stopping
7. Save best model + scaler
8. Test with best model
"""

import torch
import torch.nn.functional as F
from torch_geometric.loader import DataLoader
import numpy as np
from tqdm import tqdm
from pathlib import Path
import json
from typing import Tuple, Dict

# Import project modules
from ..models.gcn import WiFi7AttackGCN
from ..data.splits import split_files_by_scenario
from ..data.dataset import create_datasets_with_scaler
from .config import TrainingConfig
from .metrics import (
    compute_class_weights,
    compute_metrics,
    print_metrics,
    plot_confusion_matrix,
    plot_training_history,
    evaluate_model
)


def train_epoch(model, loader, optimizer, criterion, device):
    """
    Train for one epoch.

    Args:
        model: GCN model
        loader: Training data loader
        optimizer: Optimizer
        criterion: Loss function
        device: Device to train on

    Returns:
        Average loss for the epoch
    """
    model.train()
    total_loss = 0
    num_samples = 0

    for data in tqdm(loader, desc="Training", leave=False):
        data = data.to(device)

        optimizer.zero_grad()

        # Forward pass
        out = model(data.x, data.edge_index, data.batch)

        # Compute loss
        loss = criterion(out, data.y)

        # Backward pass
        loss.backward()
        optimizer.step()

        # Accumulate loss
        batch_size = data.num_graphs
        total_loss += loss.item() * batch_size
        num_samples += batch_size

    avg_loss = total_loss / num_samples
    return avg_loss


def train_wifi7_gcn(config: TrainingConfig) -> Tuple[WiFi7AttackGCN, Dict]:
    """
    Complete training pipeline for WiFi7AttackGCN.

    This function orchestrates the entire training process:
    1. Set random seeds for reproducibility
    2. Load and split files (file-level splitting!)
    3. Create datasets with scaler (fit on training data only!)
    4. Initialize model, optimizer, loss, scheduler
    5. Training loop with validation
    6. Early stopping
    7. Save best model and scaler
    8. Test with best model

    Args:
        config: Training configuration

    Returns:
        Tuple of (trained_model, test_metrics)

    Example:
        >>> from src.training.config import TrainingConfig
        >>> config = TrainingConfig()
        >>> model, test_metrics = train_wifi7_gcn(config)
        >>> print(f"Test F1: {test_metrics['f1']:.4f}")
    """
    # ========== Setup ==========
    print("="*70)
    print("WiFi 7 Backoff Attack Detection - GCN Training")
    print("="*70)

    # Set random seeds
    torch.manual_seed(config.random_seed)
    np.random.seed(config.random_seed)

    # Determine device
    if config.device:
        device = torch.device(config.device)
    else:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    print(f"\nDevice: {device}")

    # Create directories
    config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    config.log_dir.mkdir(parents=True, exist_ok=True)

    # ========== Load and Split Data ==========
    print("\n" + "="*70)
    print("LOADING AND SPLITTING DATA")
    print("="*70)

    attack_folder = config.data_root / "Attack"
    normal_folder = config.data_root / "Normal"

    train_files, val_files, test_files = split_files_by_scenario(
        attack_folder,
        normal_folder,
        test_size=config.test_size,
        val_size=config.val_size,
        random_state=config.random_seed
    )

    # ========== Create Datasets ==========
    print("\n" + "="*70)
    print("CREATING DATASETS")
    print("="*70)

    train_dataset, val_dataset, test_dataset, scaler = create_datasets_with_scaler(
        train_files,
        val_files,
        test_files,
        segment_length=config.segment_length,
        use_derived_features=config.use_derived_features
    )

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=config.batch_size,
        shuffle=False
    )

    print(f"\nData loaders created:")
    print(f"  Train batches: {len(train_loader)}")
    print(f"  Val batches: {len(val_loader)}")
    print(f"  Test batches: {len(test_loader)}")

    # ========== Initialize Model ==========
    print("\n" + "="*70)
    print("INITIALIZING MODEL")
    print("="*70)

    model = WiFi7AttackGCN(
        in_channels=config.in_channels,
        hidden_channels=config.hidden_channels,
        num_layers=config.num_layers,
        dropout=config.dropout,
        pooling=config.pooling
    ).to(device)

    print(model)
    print(f"\nTotal parameters: {model.count_parameters():,}")

    # ========== Loss and Optimizer ==========
    # Compute class weights for imbalanced dataset
    if config.use_class_weights:
        train_labels = [data.y.item() for data in train_dataset]
        class_weights = compute_class_weights(train_labels).to(device)
        criterion = torch.nn.CrossEntropyLoss(weight=class_weights)
        print(f"\nClass weights: {class_weights.cpu().numpy()}")
    else:
        criterion = torch.nn.CrossEntropyLoss()

    # Optimizer
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay
    )

    # Learning rate scheduler
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode='max',  # Maximize F1
        factor=0.5,
        patience=10,
        verbose=True
    )

    # ========== Training Loop ==========
    print("\n" + "="*70)
    print("TRAINING")
    print("="*70)

    best_val_f1 = 0.0
    patience_counter = 0
    history = {
        'train_loss': [],
        'val_metrics': []
    }

    for epoch in range(1, config.max_epochs + 1):
        # Train
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)

        # Validate
        val_metrics = evaluate_model(model, val_loader, device)

        # Update learning rate
        scheduler.step(val_metrics['f1'])

        # Record history
        history['train_loss'].append(train_loss)
        history['val_metrics'].append(val_metrics)

        # Print progress
        print(f"Epoch {epoch:03d}/{config.max_epochs} | "
              f"Loss: {train_loss:.4f} | "
              f"Val F1: {val_metrics['f1']:.4f} | "
              f"Val Acc: {val_metrics['accuracy']:.4f} | "
              f"Val AUC: {val_metrics['auc']:.4f}")

        # Save best model
        if val_metrics['f1'] > best_val_f1:
            best_val_f1 = val_metrics['f1']
            patience_counter = 0

            # Save model checkpoint
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_f1': best_val_f1,
                'config': config.to_dict()
            }

            checkpoint_path = config.checkpoint_dir / 'best_model.pt'
            torch.save(checkpoint, checkpoint_path)

            # Save scaler
            scaler_dict = {
                'mean': scaler.mean_.tolist(),
                'std': scaler.scale_.tolist()
            }

            scaler_path = config.checkpoint_dir / 'scaler.json'
            with open(scaler_path, 'w') as f:
                json.dump(scaler_dict, f, indent=2)

            print(f"  ✓ Saved best model (F1: {best_val_f1:.4f})")

        else:
            patience_counter += 1

        # Early stopping
        if patience_counter >= config.patience:
            print(f"\n⚠ Early stopping at epoch {epoch} (patience: {config.patience})")
            break

    # ========== Test with Best Model ==========
    print("\n" + "="*70)
    print("TESTING WITH BEST MODEL")
    print("="*70)

    checkpoint = torch.load(config.checkpoint_dir / 'best_model.pt')
    model.load_state_dict(checkpoint['model_state_dict'])
    print(f"Loaded best model from epoch {checkpoint['epoch']} (Val F1: {checkpoint['val_f1']:.4f})")

    test_metrics = evaluate_model(model, test_loader, device)

    # Print test results
    print_metrics(test_metrics, prefix="TEST")

    # ========== Save Results and Plots ==========
    # Save test results
    test_results_path = config.checkpoint_dir / 'test_results.json'
    with open(test_results_path, 'w') as f:
        # Convert numpy arrays to lists for JSON serialization
        test_results_json = {
            'accuracy': float(test_metrics['accuracy']),
            'precision': float(test_metrics['precision']),
            'recall': float(test_metrics['recall']),
            'f1': float(test_metrics['f1']),
            'auc': float(test_metrics['auc']),
            'confusion_matrix': test_metrics['confusion_matrix'].tolist(),
            'best_epoch': int(checkpoint['epoch']),
            'best_val_f1': float(checkpoint['val_f1'])
        }
        json.dump(test_results_json, f, indent=2)

    print(f"\nTest results saved to: {test_results_path}")

    # Plot confusion matrix
    cm_path = config.log_dir / 'confusion_matrix.png'
    plot_confusion_matrix(
        test_metrics['confusion_matrix'],
        save_path=str(cm_path),
        title="Test Set Confusion Matrix"
    )

    # Plot training history
    history_path = config.log_dir / 'training_history.png'
    plot_training_history(
        history['train_loss'],
        history['val_metrics'],
        save_path=str(history_path)
    )

    # Save configuration
    config_path = config.checkpoint_dir / 'config.yaml'
    config.save(config_path)
    print(f"Configuration saved to: {config_path}")

    # ========== Final Summary ==========
    print("\n" + "="*70)
    print("TRAINING COMPLETE")
    print("="*70)
    print(f"Best Val F1:  {best_val_f1:.4f}")
    print(f"Test F1:      {test_metrics['f1']:.4f}")
    print(f"Test Recall:  {test_metrics['recall']:.4f} ← Attacks detected")
    print(f"Test AUC:     {test_metrics['auc']:.4f}")
    print(f"\nModel saved to: {config.checkpoint_dir / 'best_model.pt'}")
    print(f"Scaler saved to: {config.checkpoint_dir / 'scaler.json'}")
    print("="*70)

    return model, test_metrics


if __name__ == "__main__":
    # Test training pipeline
    from .config import TrainingConfig

    # Use FAST_CONFIG for quick testing
    config = TrainingConfig(
        hidden_channels=32,
        num_layers=2,
        batch_size=16,
        max_epochs=5,  # Very short for testing
        patience=2,
        segment_length=256
    )

    print("Testing training pipeline with minimal configuration...")
    model, test_metrics = train_wifi7_gcn(config)

    print("\n✓ Training pipeline working correctly!")
