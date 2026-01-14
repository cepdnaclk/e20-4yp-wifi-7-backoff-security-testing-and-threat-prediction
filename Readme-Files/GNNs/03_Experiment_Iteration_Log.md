# Experiment and Iteration Log

This document serves as a log of the various experimental runs conducted for this project. The data files, located in the `data/attack/` directory, are named systematically to reflect a rigorous and iterative testing process. This process is crucial for understanding the model's performance under a wide variety of conditions.

## Naming Convention

The experiment data files follow a clear pattern:
`session_<S>_scenario_<C>_<bias_type>_bias_<B>_run_<R>.json`

-   `S`: The session number (e.g., 1, 2, 3). Represents a distinct period or environment of data collection.
-   `C`: The scenario number (e.g., 1, 2, 3, 4). Represents a specific sequence of events or a particular attack vector being tested.
-   `bias_type`: The nature of the attack, either `positive` or `negative`.
-   `B`: The magnitude of the bias applied (e.g., 50, 100, 1000, etc.). This shows an iterative increase in the intensity of the variable being tested.
-   `R`: A unique run identifier for the specific configuration.

## Log of Experimental Iterations

The following is a summary of the experimental conditions that have been generated. This demonstrates a comprehensive effort to build a robust dataset covering multiple scenarios and varying parameters.

### Session 1

-   **Scenario 1:** Tested with both `positive` and `negative` bias across a wide range of magnitudes (50, 100, 250, 500, 1000, 5000, 10000).
-   **Scenario 2:** Tested with both `positive` and `negative` bias across the same range of magnitudes.
-   **Scenario 3:** Tested with both `positive` and `negative` bias across the same range of magnitudes.
-   **Scenario 4:** Tested with both `positive` and `negative` bias across the same range of magnitudes.

### Session 2

-   **Scenario 1:** Duplicates the conditions of Session 1, Scenario 1, likely to test for consistency or under slightly different initial conditions.
-   **Scenario 2:** Duplicates the conditions of Session 1, Scenario 2.
-   **Scenario 3:** Duplicates the conditions of Session 1, Scenario 3.
-   **Scenario 4:** Duplicates the conditions of Session 1, Scenario 4.

### Session 3

-   **Scenario 1:** Further duplication of the same experimental conditions.
-   **Scenario 2:** Further duplication of the same experimental conditions.
-   **Scenario 3:** Further duplication of the same experimental conditions.
-   **Scenario 4:** Further duplication of the same experimental conditions.

## Interpretation of Progress

This structured approach to data generation is a form of iterative development. By systematically varying the `session`, `scenario`, and `bias`, you have created a rich dataset that allows for in-depth analysis of the GNN model's capabilities:

1.  **Robustness Testing:** By training and evaluating the model on data from different sessions and scenarios, you can measure how well it generalizes to different situations.
2.  **Sensitivity Analysis:** The incremental changes in the `bias` magnitude are particularly valuable. This allows you to pinpoint the model's sensitivity. For example, you can determine the minimum bias magnitude at which the model can successfully detect an anomaly.
3.  **Progressive Improvement:** Having multiple versions (sessions) allows for regression testing. As you improve the GNN model (e.g., by tuning hyperparameters or changing its architecture), you can re-run the evaluation on this comprehensive dataset to ensure that improvements in one area do not cause performance to degrade in another.

This experimental log clearly shows a methodical and iterative process, which is fundamental to building a high-performing and reliable machine learning model.
