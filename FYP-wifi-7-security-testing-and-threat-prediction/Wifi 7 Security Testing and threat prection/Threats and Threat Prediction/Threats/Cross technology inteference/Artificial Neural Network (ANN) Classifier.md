### **Architecture**

- **Input layer:** 9 neurons
    
    - 8 = normalized error counters
        
    - 1 = maximum inter-error time
        
- **Hidden layer:** 24 neurons
    
- **Output layer:** 4 neurons (WiFi, ZigBee, LTE-U, Microwave)
    
- Trained with **scikit-learn (Python)** using **L-BFGS optimizer** and **tanh activation**.
    

### **Training**

- Dataset: 6078 training samples, 2606 test samples.
    
- **Cross-validation (10-fold)** for hyperparameter tuning.
    
- Optimal hyperparameters:
    
    - Solver: **L-BFGS** (fastest convergence, 94.5% accuracy)
        
    - Regularization α = 0.1
        
    - Activation = **tanh**
        

### **Results**

- **Test accuracy:** 95.3%
    
- **Full dataset accuracy:** 94–99% depending on interference source.
    
- ANN performed **better than HMM**, especially when aggregating per-burst features rather than analyzing event sequences