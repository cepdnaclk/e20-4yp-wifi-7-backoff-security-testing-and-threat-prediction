import torch
import torch.nn as nn
import torch.nn.functional as F

class AttackGCN(nn.Module):
    """
    Input:
      A: [N,N] normalized adjacency (between windows)
      X: [N,F] node features (per-window feature vectors)
    Output:
      logits: [3] (logits for 3 classes: normal, positive attack, negative attack)
    """
    def __init__(self, in_dim: int = 14, hidden: int = 32, n_classes: int = 3):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.cls = nn.Linear(hidden, n_classes)

    def forward(self, A: torch.Tensor, X: torch.Tensor) -> torch.Tensor:
        # GCN layer 1
        H = torch.matmul(A, X)
        H = F.relu(self.fc1(H))

        # GCN layer 2
        H = torch.matmul(A, H)
        H = F.relu(self.fc2(H))

        # graph pooling (mean)
        g = H.mean(dim=0)          # [hidden]
        logits = self.cls(g)
        return logits
