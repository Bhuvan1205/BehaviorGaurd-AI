# BehaviorGuard-AI
BehaviorGuard-AI is a research-oriented **User and Entity Behavior Analytics (UEBA)** system designed to detect potential insider threats within enterprise environments. The system addresses the challenge of identifying malicious or compromised insiders who operate within authorized access boundaries, making them invisible to traditional perimeter security tools. The core ML approach combines **contextual user profiling**, **statistical behavioral baselines**, **unsupervised anomaly detection** using Isolation Forest, and **peer-aware behavioral clustering** to produce calibrated, low–false-positive anomaly alerts across organizational shifts.
---
## Problem Statement
Insider threats represent one of the most damaging and difficult-to-detect categories of cybersecurity risk. Unlike external attackers, insiders already possess legitimate credentials and authorized access to organizational systems, rendering traditional defenses such as firewalls and intrusion detection systems largely ineffective.
Key challenges include:
- **Behavioral ambiguity** — insiders operate within normal access patterns, making malicious activity difficult to distinguish from routine work.
- **Absence of labeled data** — verified insider threat datasets are extremely rare in practice, ruling out supervised classification approaches.
- **Structural heterogeneity** — user populations contain diverse behavioral archetypes (e.g., low-activity stable users vs. high-volume power users), causing global anomaly models to inflate false positives.
- **Temporal variability** — legitimate behavior varies significantly across time-of-day shifts, requiring shift-aware analysis.
Without a system like BehaviorGuard-AI, organizations must rely on static rule-based alerts that generate excessive false positives, miss subtle behavioral deviations, and lack the contextual awareness needed to prioritize genuine threats.
---
## Project Overview
BehaviorGuard-AI implements an end-to-end behavioral analytics pipeline that progresses through six iterative versions (V0–V6), each building upon the previous:
1. **Data Ingestion** — Raw authentication logs (`logon.csv`, ~3.5M records) and employee metadata (`users.csv`, ~4,000 users) are loaded from the CERT insider threat dataset.
2. **Preprocessing** — Timestamps are parsed, categorical fields are normalized to lowercase, missing values are handled, and data integrity checks (nulls, duplicates) are performed.
3. **Contextual Feature Engineering (V0)** — User profiles are built from organizational metadata, including role-based privilege flags, tenure calculations, supervisor/project assignment checks, rare role detection, and a weighted contextual risk score.
4. **Behavioral Feature Engineering (V1)** — Raw logon events are aggregated into hourly time windows per user, producing features such as logon count, logoff count, unique device count, and per-user Z-score deviations for logon frequency and device usage.
5. **Shift Segmentation (V3+)** — Activity is partitioned into Day (09:00–16:00), Evening (17:00–21:00), and Night (22:00–08:00) shifts to account for temporal behavioral differences.
6. **User Clustering (V3+)** — Per-shift user behavioral profiles (mean/std of logon counts, device usage, activity hour) are constructed and clustered into 4 peer groups using KMeans, creating behavioral archetype segments.
7. **Anomaly Detection (V2–V3)** — Isolation Forest models are trained independently within each cluster-shift combination, scoring hourly records on activity features. Percentile-based threshold calibration (1st percentile) replaces the default zero-threshold to control alert rates.
8. **Synthetic Validation (V4)** — Synthetic anomalies (login bursts, device explosions, cross-shift activity, combined anomalies) are injected at 0.5% of data volume to evaluate detection capability and false positive rates.
9. **Context-Aware Clustering (V6)** — HDBSCAN-based clustering with expanded feature sets integrating contextual features (role groups, tenure, device ratios, burst scores) for density-aware behavioral segmentation.
---
## Key Features
- **Contextual User Profiling** — Constructs user risk profiles from organizational metadata using engineered features such as `is_privileged`, `is_new`, `rare_role`, `has_supervisor`, and `has_project`, combined into a weighted baseline risk score.
- **Statistical Behavioral Baselines** — Computes per-user mean and standard deviation of logon frequency and device usage, enabling individualized Z-score deviation metrics that capture abnormal behavior relative to each user's own history.
- **Shift-Aware Pipeline** — Segments all activity into Day, Evening, and Night shifts, processing each independently to prevent cross-shift contamination in behavioral modeling.
- **Peer-Group Clustering** — Uses KMeans (k=4) on aggregated user-level behavioral profiles to identify behavioral archetypes within each shift, ensuring that anomaly detection operates within homogeneous sub-populations.
- **Cluster-Specific Isolation Forest** — Trains independent Isolation Forest models per cluster-shift combination, eliminating the structural false positives caused by mixed-density global models.
- **Percentile-Based Threshold Calibration** — Replaces Isolation Forest's default contamination-based threshold with per-cluster 1st-percentile calibration, achieving stable ~1% alert rates across all shifts and clusters.
- **Synthetic Anomaly Validation (V4)** — Injects four types of synthetic anomalies (login burst, device explosion, cross-shift, combined) and evaluates detection rate and false positive rate using both percentile-calibrated and raw Isolation Forest predictions.
- **HDBSCAN Context-Aware Clustering (V6)** — Explores density-based clustering using HDBSCAN with expanded feature sets incorporating role-based groups, device ratios, burst scores, and session gaps.
- **Model Persistence** — Trained models (Isolation Forest, KMeans, StandardScaler) and threshold configurations are serialized to `.pkl` and `.json` files for reproducibility and future inference.
- **Iterative Experimentation** — Six versioned Jupyter notebooks (V0–V6) document the full research progression with detailed outputs, visualizations, and analysis.
- **Evaluation Metrics** — Detection rate, false positive rate, detection by anomaly type, and detection by shift are computed for systematic model assessment.
---
## System Architecture
The system follows a modular, layered architecture:
```
Raw Data (logon.csv, users.csv)
        │
        ▼
┌─────────────────────────┐
│   Data Preprocessing    │  ← Timestamp parsing, null handling, normalization
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Contextual Profiling   │  ← Role flags, tenure, risk score (V0)
│   (User Metadata)       │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Behavioral Feature     │  ← Hourly aggregation, Z-scores (V1)
│    Engineering          │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Shift Segmentation    │  ← Day / Evening / Night partitioning (V3)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  User Profile Building  │  ← Per-shift mean/std aggregation
│  & Peer-Group Clustering│  ← KMeans (k=4) on user profiles
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Cluster-Specific       │  ← Independent Isolation Forest per cluster
│  Anomaly Detection      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Percentile Threshold   │  ← 1st percentile calibration per cluster
│     Calibration         │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Anomaly Alerts &      │  ← Detection metrics, per-type/per-shift eval
│     Evaluation          │
└─────────────────────────┘
```
**Component Mapping:**
| Component | Location |
|---|---|
| User profiling & risk scoring | `src/features/user_profile.py` |
| V3 pipeline (shift → cluster → IF → threshold) | `notebooks/v4_pipeline.py` |
| Synthetic anomaly injection & evaluation | `notebooks/v4_pipeline.py` |
| Exploratory analysis & model development | `notebooks/V0.ipynb` – `V6.ipynb` |
| Trained models (IF, KMeans, Scalers) | `notebooks/models/`, `src/models/` |
| Threshold & feature configurations | `notebooks/models/*.json` |
| Documentation per version | `docs/paper_notes/V0.md` – `V3.md` |
---
## Machine Learning Methodology
### Models Used
| Model | Purpose | Configuration |
|---|---|---|
| **Isolation Forest** | Unsupervised anomaly detection on hourly behavioral features | `n_estimators=100`, `contamination="auto"`, `random_state=42` |
| **KMeans** | Peer-group clustering of users into behavioral archetypes | `k=4`, `n_init=10`, `random_state=42` |
| **StandardScaler** | Feature normalization prior to clustering | Applied per-shift on user profile features |
| **HDBSCAN** (V6) | Density-based clustering with noise detection | Context-aware feature set with role groups |
### Training Process
1. **Per-shift user profiles** are constructed by aggregating hourly behavioral data (mean/std of logon counts, device usage, activity hour) for each user.
2. **StandardScaler** normalizes profile features to zero mean and unit variance.
3. **KMeans** clusters users into 4 behavioral peer groups per shift.
4. Cluster labels are merged back into the hourly-level dataset.
5. **Isolation Forest** is trained independently within each cluster on activity features (`logon_count`, `logoff_count`, `unique_pcs`, `z_logon`, `z_pcs`), ensuring anomaly scoring is relative to behavioral peers.
6. Continuous `decision_function` scores are computed instead of binary predictions.
### Feature Engineering Strategy
- **Clustering features:** `mean_logon_count`, `std_logon_count`, `total_logon_volume` (log-transformed), `mean_unique_pcs`, `std_unique_pcs`, `mean_activity_hour`, `activity_hour_std`
- **Isolation Forest features:** `logon_count`, `logoff_count`, `unique_pcs`, `z_logon`, `z_pcs`
- Clustering and IF feature sets are intentionally disjoint to prevent structural leakage.
### Anomaly Scoring & Threshold Calibration
The default Isolation Forest threshold (`decision_function < 0`) was found to cause **zero-threshold bias**, where clusters with slightly negative mean scores had entire populations labeled anomalous. This was replaced with **per-cluster percentile-based calibration**:
```
threshold = cluster_scores.quantile(0.01)
alert if score < threshold
```
This ensures each cluster independently produces a ~1% alert rate, eliminating contamination dependency and cross-cluster bias.
### Model Evaluation
- **Synthetic anomaly injection (V4):** 0.5% of records are modified with four anomaly types to test detection sensitivity.
- **Detection rate** and **false positive rate** are computed for both percentile-calibrated alerts and raw IF predictions.
- **Per-type detection rates** (login burst, device explosion, cross-shift, combined) assess model sensitivity to different threat patterns.
- **Per-shift detection rates** verify consistency across Day, Evening, and Night.
- **Correlation analysis (V2):** Pearson correlation between IF anomaly scores and rule-based behavioral risk scores was used to validate the V2 baseline model (correlation: **-0.75**).
### Algorithm Selection Rationale
- **Isolation Forest** was chosen for its efficiency on high-dimensional data, its ability to directly model anomalies rather than normal-class density, and its suitability for unlabeled data — all critical requirements for real-world UEBA deployment.
- **KMeans** was selected for peer-group segmentation due to its simplicity, interpretability, and stable cluster formation on the user profile feature space.
- **HDBSCAN** (V6) was explored as an alternative for its ability to handle variable-density clusters and automatically identify noise points.
---
## Dataset
| Attribute | Details |
|---|---|
| **Source** | CERT Insider Threat Dataset (Carnegie Mellon University) |
| **Primary Files** | `logon.csv` (~241 MB, ~3.5M authentication records), `users.csv` (~805 KB, ~4,000 employees) |
| **Format** | CSV |
| **Key Fields (logon.csv)** | `user`, `pc`, `date`, `activity` (Logon/Logoff) |
| **Key Fields (users.csv)** | `employee_name`, `user_id`, `email`, `role`, `projects`, `department`, `functional_unit`, `supervisor`, `team`, `start_date`, `end_date` |
| **Processed Outputs** | `enriched_logon.csv` (~480 MB), `behavior_dataset_v5_features.csv` (~1.4 GB), `behavior_dataset_v6_clusters.csv` (~1.5 GB), `user_profiles_v0.csv` |
### Preprocessing Steps Applied
1. Timestamp conversion to datetime format
2. Null value handling (categorical fields filled with `'unassigned'`, end dates filled with current date)
3. Text normalization (lowercase conversion)
4. Duplicate removal
5. Hourly time-window aggregation of logon events per user
6. Per-user baseline statistics (mean, std of logon frequency and device usage)
7. Z-score computation for behavioral deviation metrics
8. Log transformation of total logon volume
9. Shift segmentation (Day/Evening/Night)
Raw datasets are excluded from version control via `.gitignore` due to size constraints. All preprocessing scripts and derived feature pipelines are tracked in the repository.
---
## Results and Observations
### V2 Baseline (Global Isolation Forest)
- Anomaly rate: **~1.0%** (with 1% contamination setting)
- Correlation with rule-based behavioral risk score: **-0.75** (strong negative correlation, validating that IF anomaly scores align with the behavioral risk scoring mechanism)
- Late-night activity (23:00–00:00) confirmed as a high-intensity anomaly indicator
- A small subset of users exhibited >10% anomaly rates, warranting investigation
### V3 (Peer-Aware Calibrated Pipeline)
- **Day shift** alert rate: ~0.93%
- **Evening shift** alert rate: ~0.997%
- **Night shift** alert rate: ~0.958%
- Alert rates balanced across all 4 clusters within each shift
- Structural false positives from V2 eliminated through peer-group segmentation
- Zero-threshold bias resolved via percentile calibration
### V4 (Synthetic Validation)
- Synthetic anomaly injection at 0.5% of total records
- Detection evaluated across four anomaly types: login burst, device explosion, cross-shift activity, and combined anomalies
- Both percentile-calibrated and raw Isolation Forest detection metrics computed
- Results enable comparison of thresholding strategies
### Key Findings
1. **Structural heterogeneity** within user populations inflates anomaly rates when using global density models.
2. **Peer-group segmentation** via user-level clustering significantly reduces structural false positives.
3. **Percentile-based threshold calibration** is more critical than contamination parameter tuning for achieving stable, fair alert rates.
4. The architecture **generalizes across all three shifts** under a single modeling strategy after calibration.
5. Daily regime clustering was found to be overly granular and was rolled back in favor of user-level archetype clustering.
### Limitations
- No labeled insider threat ground truth; evaluation relies on proxy metrics and synthetic injection.
- The model operates on aggregated hourly windows and does not capture sequential event dependencies.
- Current implementation is offline/batch-oriented and does not support real-time streaming.
---
## Repository Structure
```
BehaviorGuard-AI/
│
├── data/
│   ├── raw/                        # Raw datasets (logon.csv, users.csv) — gitignored
│   └── processed/                  # Derived datasets (enriched_logon, feature sets, clusters) — gitignored
│
├── notebooks/
│   ├── V0.ipynb                    # Contextual user profiling and risk scoring
│   ├── V1.ipynb                    # Behavioral feature engineering and Z-score analysis
│   ├── V2.ipynb                    # Global Isolation Forest baseline model
│   ├── V3.ipynb                    # Peer-aware clustering with percentile calibration
│   ├── V4.ipynb                    # Synthetic anomaly injection and validation
│   ├── V5.ipynb                    # Extended feature engineering experiments
│   ├── V6.ipynb                    # HDBSCAN context-aware clustering
│   ├── v4_pipeline.py              # Consolidated V3/V4 pipeline module
│   ├── models/                     # Trained V3 models (KMeans, IF, Scalers, thresholds)
│   ├── artifacts/                  # Intermediate outputs (user profiles per shift)
│   └── if_tuning_results.csv       # Isolation Forest hyperparameter tuning log
│
├── src/
│   ├── features/
│   │   └── user_profile.py         # User profiling pipeline (load, clean, feature engineering, risk score)
│   ├── models/
│   │   ├── if_v2_baseline.pkl      # Serialized V2 Isolation Forest baseline model
│   │   └── if_v2_baseline_metadata.json  # V2 model metadata and performance metrics
│   ├── evaluation/                 # Evaluation utilities (placeholder)
│   ├── ingestion/                  # Data ingestion utilities (placeholder)
│   └── preprocessing/              # Preprocessing utilities (placeholder)
│
├── api/                            # API development (placeholder for FastAPI deployment)
│
├── frontend/
│   └── dashboard/                  # Dashboard interface (placeholder)
│
├── docs/
│   ├── paper_notes/
│   │   ├── V0.md                   # Documentation: Contextual Profiling
│   │   ├── V1.md                   # Documentation: Statistical Behavioral Modeling
│   │   ├── V2.md                   # Documentation: Unsupervised Anomaly Detection
│   │   └── V3.md                   # Documentation: Peer-Aware Anomaly Calibration
│   ├── v2_anomaly_by_hour.png      # Visualization: anomaly distribution by hour
│   └── v2_top_users.png            # Visualization: top flagged users
│
├── requirements.txt                # Python dependencies
├── .gitignore                      # Version control exclusions
└── README.md                       # This file
```
---
## Installation
### Prerequisites
- Python 3.10+
- pip
### Steps
1. **Clone the repository:**
   ```bash
   git clone https://github.com/Bhuvan1205/BehaviorGaurd-AI.git
   cd BehaviorGaurd-AI
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up the dataset:**
   - Obtain the CERT Insider Threat Dataset.
   - Place `logon.csv` and `users.csv` in the `data/raw/` directory.
5. **Generate user profiles:**
   ```bash
   python src/features/user_profile.py
   ```
---
## Usage
### Running the Notebooks
Launch Jupyter and open the versioned notebooks in order:
```bash
jupyter notebook notebooks/
```
- **V0.ipynb** — Run contextual user profiling and risk scoring.
- **V1.ipynb** — Run behavioral feature engineering and aggregation.
- **V2.ipynb** — Train and evaluate the global Isolation Forest baseline.
- **V3.ipynb** — Execute the peer-aware clustering and calibrated anomaly detection pipeline.
- **V4.ipynb** — Run synthetic anomaly injection and validate detection performance.
- **V5.ipynb** — Experiment with extended feature sets.
- **V6.ipynb** — Explore HDBSCAN-based context-aware clustering.
### Running the V4 Pipeline Programmatically
```python
import pandas as pd
from notebooks.v4_pipeline import run_full_v4_pipeline, display_metrics
# Load preprocessed behavioral data
df = pd.read_csv("data/processed/enriched_logon.csv")
# Run full pipeline (injection → detection → evaluation)
df_result, metrics = run_full_v4_pipeline(df)
# Display evaluation results
display_metrics(metrics["percentile_calibrated"], title="Percentile-Calibrated Detection")
display_metrics(metrics["raw_if"], title="Raw Isolation Forest Detection")
```
### Building User Profiles
```python
from src.features.user_profile import build_user_profile
build_user_profile("data/raw/users.csv", "data/processed/user_profiles_v0.csv")
```
---
## Future Improvements
- **Sequence-Aware Models** — Incorporate recurrent neural networks (LSTMs) or Transformer-based architectures to capture temporal dependencies between sequential logon events.
- **Autoencoder-Based Detection** — Implement deep autoencoder models for reconstruction-error-based anomaly scoring as a complementary approach to Isolation Forest.
- **Contextual Risk Fusion** — Integrate the contextual risk scores (V0) with behavioral anomaly scores (V3+) into a unified, multi-signal threat scoring framework.
- **Real-Time Streaming Pipeline** — Transition from batch processing to real-time event processing using streaming frameworks for live monitoring.
- **API Deployment** — Build a FastAPI-based REST API for serving anomaly predictions and user risk scores in production environments.
- **Dashboard Implementation** — Develop an interactive dashboard for security analysts to visualize alerts, user profiles, and behavioral trends.
- **Multi-Log Correlation** — Extend analysis beyond logon data to include file access, email, USB device usage, and HTTP activity logs.
- **Production Monitoring** — Add model drift detection, alert rate monitoring, and automated retraining triggers.
- **Expanded Evaluation** — Incorporate precision-recall analysis, ROC curves, and holdout temporal validation for more rigorous model assessment.

- *Developed as a B.Tech Mini Project with emphasis on clean architecture, modular design, and research-oriented machine learning practices.*
