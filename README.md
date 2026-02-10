# BehaviorGuard-AI

BehaviorGuard-AI is a research-oriented User and Entity Behavior Analytics (UEBA) system designed to detect potential insider threats. The project adopts a layered approach, moving from contextual profiling to advanced machine learning-driven behavioral analytics.

## Project Structure

- `docs/`: Project documentation and visualizations.
- `notebooks/`: Exploratory Data Analysis (EDA) and model development.
- `src/`: Source code for the modeling pipeline.
- `data/`: Local storage for raw and processed datasets (excluded from version control).

## Documentation Versions

The project documentation is organized by version to track the evolution of the system:

1. **[Version 0: Contextual Profiling](docs/paper_notes/V0.md)**  
   Focuses on building a robust user profiling and baseline risk scoring layer.
   
2. **[Version 1: Statistical Behavioral Modeling](docs/paper_notes/V1.md)**  
   Introduces behavioral analysis based on system logon records and statistical deviation analysis (Z-scores).

3. **[Version 2: Unsupervised Anomaly Detection](docs/paper_notes/V2.md)**  
   Implements an Isolation Forest-based machine learning framework for learning normal behavioral patterns and identifying outliers.

---
*Developed as a B.Tech Mini Project with an emphasis on clean architecture and modular design.*