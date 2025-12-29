# GNN/model.py
import torch
import torch.nn as nn
import torch.nn.functional as F

class GCNLayer(nn.Module):
    def __init__(self, in_dim, out_dim):
        super().__init__()
        self.lin = nn.Linear(in_dim, out_dim)

    def forward(self, A_norm, X):
        # A_norm: [N,N], X: [N,F]
        return self.lin(A_norm @ X)

class GraphAttackDetector(nn.Module):
    def __init__(self, in_dim, hidden=64):
        super().__init__()
        self.g1 = GCNLayer(in_dim, hidden)
        self.g2 = GCNLayer(hidden, hidden)
        self.head = nn.Linear(hidden, 1)   # graph logit

    def forward(self, A_norm, X):
        h = F.relu(self.g1(A_norm, X))
        h = F.relu(self.g2(A_norm, h))
        g = h.mean(dim=0)                  # mean pool -> graph embedding
        logit = self.head(g)               # [1]
        return logit
