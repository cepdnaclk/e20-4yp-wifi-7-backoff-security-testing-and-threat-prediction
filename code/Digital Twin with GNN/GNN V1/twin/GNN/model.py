import torch
import torch.nn as nn
import torch.nn.functional as F

class GCNLayer(nn.Module):
    def __init__(self, in_dim, out_dim):
        super().__init__()
        self.lin = nn.Linear(in_dim, out_dim)

    def forward(self, A_norm, X):
        # A_norm: [N,N], X:[N,F]
        return self.lin(A_norm @ X)

class GNNRegressor(nn.Module):
    def __init__(self, in_dim=3, hidden=32, node_out=3):
        super().__init__()
        self.gcn1 = GCNLayer(in_dim, hidden)
        self.gcn2 = GCNLayer(hidden, hidden)
        self.node_head = nn.Linear(hidden, node_out)  # per-STA KPIs
        self.global_head = nn.Linear(hidden, 1)        # fairness

    def forward(self, A_norm, X):
        h = F.relu(self.gcn1(A_norm, X))
        h = F.relu(self.gcn2(A_norm, h))

        node_pred = self.node_head(h)                 # [N, node_out]
        graph_emb = h.mean(dim=0, keepdim=True)       # [1, hidden]
        global_pred = self.global_head(graph_emb)     # [1,1]
        return node_pred, global_pred.squeeze(0)      # ([N,3], [1])
