# BehaviorGuard-AI
BehaviorGuard-AI is a research-oriented User and Entity Behavior Analytics (UEBA) system designed to detect insider threats within enterprise environments using behavioral anomaly detection. The system analyzes authentication activity patterns to identify deviations from established behavioral baselines using unsupervised machine learning and contextual profiling.

The project explores how large-scale authentication logs can be transformed into behavioral signals that reveal suspicious activity even when attackers operate within legitimate access privileges.

---

## Key Highlights

• Behavioral anomaly detection using Isolation Forest  
• Peer-group clustering to reduce structural false positives  
• Shift-aware behavioral modeling (Day / Evening / Night)  
• Synthetic anomaly injection for model validation  
• Built on the CERT Insider Threat Dataset (~3.5M authentication events)

---

## Problem Statement

Insider threats represent one of the most challenging cybersecurity risks. Unlike external attackers, insiders already possess legitimate credentials and authorized access to organizational systems, making traditional perimeter security tools ineffective.

Key challenges include:

- **Behavioral ambiguity:** malicious insiders often mimic legitimate usage patterns  
- **Absence of labeled data:** real insider threat labels are extremely rare  
- **User heterogeneity:** different users exhibit very different activity profiles  
- **Temporal variation:** behavior changes across work shifts

BehaviorGuard-AI investigates whether unsupervised behavioral modeling can identify suspicious activity patterns without requiring labeled attack data.

---

## Project Overview

The system builds a behavioral analytics pipeline using enterprise authentication logs.

Pipeline stages:

1. **Data Ingestion**
   - CERT insider threat dataset
   - ~3.5M authentication records

2. **Preprocessing**
   - timestamp normalization
   - categorical cleaning
   - missing value handling

3. **Contextual User Profiling**
   - tenure
   - role privilege indicators
   - organizational metadata
   - contextual risk scoring

4. **Behavioral Feature Engineering**
   - hourly logon counts
   - device usage patterns
   - statistical deviation metrics (Z-scores)

5. **Shift Segmentation**
   - Day (09:00–16:00)
   - Evening (17:00–21:00)
   - Night (22:00–08:00)

6. **Peer-Group Clustering**
   - KMeans clustering of user behavioral profiles
   - formation of behavioral archetypes

7. **Cluster-Specific Anomaly Detection**
   - Isolation Forest models trained independently per cluster

8. **Threshold Calibration**
   - percentile-based anomaly thresholds to stabilize alert rates

9. **Synthetic Validation**
   - injection of artificial anomalies to evaluate detection performance

---

## System Architecture

Raw Logs (CERT Dataset)
↓
Preprocessing
↓
Contextual Profiling
↓
Behavioral Feature Engineering
↓
Shift Segmentation
↓
User Clustering (KMeans)
↓
Cluster-Specific Isolation Forest
↓
Percentile Threshold Calibration
↓
Anomaly Alerts


---

## Machine Learning Methodology

### Isolation Forest
Used for unsupervised anomaly detection on behavioral features.

**Configuration**

- n_estimators = 100  
- contamination = auto  
- random_state = 42

### KMeans Clustering

Used to segment users into behavioral archetypes.

**Configuration**

- k = 4 clusters  
- n_init = 10

### HDBSCAN (Experimental)

Explored in later iterations to support density-aware clustering.

---

## Dataset

**Source:** CERT Insider Threat Dataset (Carnegie Mellon University)

Files:

| File | Description |
|-----|-------------|
| logon.csv | Authentication logs |
| users.csv | Employee metadata |

Dataset scale:

- ~3.5M authentication records  
- ~4,000 employees

---

## Results & Observations

Key findings from the experimentation pipeline:

• Global anomaly models generate structural false positives due to heterogeneous user behavior  
• Peer-group segmentation significantly improves anomaly stability  
• Percentile threshold calibration produces consistent alert rates across clusters  
• Late-night authentication activity is a strong anomaly indicator  

---

## Repository Structure


BehaviorGuard-AI
│
├── data
│ ├── raw
│ └── processed
│
├── notebooks
│ ├── V0.ipynb
│ ├── V1.ipynb
│ ├── V2.ipynb
│ ├── V3.ipynb
│ ├── V4.ipynb
│ ├── V5.ipynb
│ └── V6.ipynb
│
├── src
│ ├── features
│ ├── models
│ ├── ingestion
│ ├── preprocessing
│ └── evaluation
│
├── api
├── frontend
├── docs
└── README.md


---

## Future Work

• Sequence-aware models (LSTM / Transformer) for temporal behavior modeling  
• Real-time streaming anomaly detection pipelines  
• Fusion of contextual and behavioral risk scores  
• Multi-log correlation (email, file access, HTTP activity)  
• Interactive analyst dashboard

---

## Author

Bhuvanesh  
GitHub: https://github.com/Bhuvan1205
