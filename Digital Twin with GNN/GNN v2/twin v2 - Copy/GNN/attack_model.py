import torch
import torch.nn as nn
import torch.nn.functional as F

class AttackGCN(nn.Module):
    """
    Input:
      A: [N,N] normalized adjacency
      X: [N,F] node features
    Output:
      logit: scalar (attack logit)
    """
    def __init__(self, in_dim: int = 8, hidden: int = 32):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.cls = nn.Linear(hidden, 1)

    def forward(self, A: torch.Tensor, X: torch.Tensor) -> torch.Tensor:
        # GCN layer 1
        H = torch.matmul(A, X)
        H = F.relu(self.fc1(H))

        # GCN layer 2
        H = torch.matmul(A, H)
        H = F.relu(self.fc2(H))

        # graph pooling (mean)
        g = H.mean(dim=0)          # [hidden]
        logit = self.cls(g).squeeze(-1)
        return logit
