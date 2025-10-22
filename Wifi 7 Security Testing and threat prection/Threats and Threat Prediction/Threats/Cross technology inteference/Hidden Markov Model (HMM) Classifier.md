- The HMM models **receiver state transitions**:
    
    - `START`, `NO_SYNC`, `SYNC`, `END`.
        
- **Emission probabilities**: likelihood of each error vector given a state.
    
- Separate HMMs trained for each interference type (WiFi, ZigBee, LTE-U, Microwave) using **Baum–Welch algorithm**.
    

### **Results:**

- Classification accuracy: **≈90% average**.
    
- Misclassifications mostly between LTE-U and ZigBee (similar temporal patterns).
    
- Robust even when interference duration changes (e.g., 10 ms → 5 ms LTE frame)