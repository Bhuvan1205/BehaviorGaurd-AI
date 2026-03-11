BehaviorGuard-AI
(DOCUMENTATION-6)
Version 5 – Advanced Feature Engineering & Behavioral Context Expansion
1. Objective of Version 5
The objective of Version 5 (V5) was to improve anomaly detection performance by expanding the behavioral feature space and integrating organizational context into the UEBA system.
Earlier versions relied mainly on:
•	raw activity counts
•	statistical normalization features
•	shift-based segmentation
However, behavioral overlap in the dataset made it difficult for Isolation Forest to clearly distinguish anomalous behavior.
Therefore, V5 focused on:
•	expanding behavioral features
•	integrating organizational role information
•	improving contextual user grouping
•	preparing the dataset for advanced clustering techniques
This version represents a major feature engineering and contextual modeling milestone rather than a redesign of the detection model.
2. Dataset Overview
The V5 dataset is derived from the enriched logon dataset and contains hourly aggregated user activity.
Dataset characteristics:
•	Total Records: 3,366,264
•	Time Range: Jan 2010 – Jun 2011
•	Unique Users: ~3000
•	Aggregation Level: Hourly per user
Example structure:
user | window | logon_count | logoff_count | unique_pcs | hour
This hourly aggregation enables detection of temporal behavioral deviations.
3. Baseline Behavioral Features
Before V5, the system already used core behavioral indicators.
Core Activity Features
logon_count
logoff_count
unique_pcs
hour
Behavioral Baseline Features
avg_logon
std_logon
avg_pcs
std_pcs
Normalized Indicators
z_logon
z_pcs
These features capture how far user activity deviates from normal behavioral patterns.
4. Feature Engineering Introduced in V5
V5 significantly expanded the feature space with derived behavioral indicators.
4.1 Logon Deviation
logon_deviation
Measures deviation from historical login behavior.
Purpose: detect abnormal login spikes.
4.2 Device Deviation
device_deviation
Captures deviation in the number of devices used.
Example: user normally uses 1 device but suddenly logs in from 4–5 devices.
4.3 Logon-Logoff Ratio
logon_logoff_ratio
Measures imbalance between login and logout events.
Purpose: detect repeated logins or irregular sessions.
4.4 Burst Score
burst_score
Captures rapid login bursts within short time windows.
Useful for detecting credential testing or automated login attempts.
4.5 Device Ratio
device_ratio
Measures device usage relative to historical baseline.
4.6 Hour Deviation
hour_deviation
Measures deviation from normal login time.
Example: user typically logs in during office hours but suddenly accesses the system at night.
4.7 Session Gap
session_gap
Measures time difference between activity windows.
Large gaps indicate long idle periods followed by sudden activity.
4.8 Night Activity Flag
night_activity_flag
Binary indicator identifying night-time activity.
Used to highlight behavior outside normal working hours.
5. Dataset Statistical Summary
Key statistics after feature engineering:
Device Usage
Mean unique_pcs : 1.007
STD unique_pcs  : 0.727
Interpretation: most users operate from a single device, making multi-device activity suspicious.
Logon Activity
Average logon_count : 0.55
STD logon_count     : 0.51
Login activity per hour is generally low.
Session Gap
Mean session_gap : 13.98
STD session_gap  : 16.02
Max session_gap  : 114
Large gaps correspond to long inactivity periods.
6. Correlation Analysis
Correlation analysis identified strong relationships between several features.
Strong Positive Correlations
logon_count ↔ z_logon : 0.98
unique_pcs ↔ z_pcs    : 0.79
Normalized features accurately capture underlying behavioral signals.
Strong Negative Correlation
logon_count ↔ logoff_count : -0.84
This reflects normal session behavior patterns.
7. Organizational Context Integration
To enhance behavioral context, V5 incorporated organizational role information from the HR dataset.
The dataset contained 46 unique roles, such as:
•	software engineer
•	mechanical engineer
•	technician
•	salesman
•	scientist
•	IT administrator
Modeling each role separately would create sparse datasets, so role grouping was required.
8. Role Grouping Strategy
Roles were consolidated into broader functional groups to improve modeling stability.
Final role groups:
engineering
operations
software_engineering
sales
it_admin
research
logistics
admin_staff
management
healthcare
finance
This grouping preserved behavioral similarity while ensuring sufficient data per group.
9. Role Group Distribution
Dataset distribution after grouping:
engineering                      934,678
operations                        713,487
software_engineering      412,496
sales                              297,986
it_admin                        256,799
research                         253,326
logistics                         233,443
admin_staff                   125,955
management                 108,604
healthcare                      23,327
finance                           6,163
This ensured each role group contained enough data for reliable modeling.
10. Contextual Behavioral Modeling
V5 introduced two-level contextual segmentation.
Level 1 – Shift Segmentation
Day     : 09–16
Evening : 17–21
Night   : 22–08
Captures temporal behavioral differences.
Level 2 – Role Group Segmentation
Within each shift, users are grouped by role group.
Examples:
•	Day – Software Engineering
•	Evening – Operations
•	Night – IT Admin
This ensures users are compared only with behaviorally similar peers.
11. Behavioral Clustering
Within each shift + role group context, clustering was applied to identify micro behavioral patterns.
Example context:
Day | Software Engineering
Cluster distribution:
Cluster 0 : 58,954
Cluster 1 : 70,672
This indicates multiple behavioral modes within the same role group.
12. Anomaly Detection Experiments
Isolation Forest remained the anomaly detection model.
Two evaluation strategies were tested.
12.1 Percentile-Calibrated Detection
Threshold adjusted to maintain ~1% alert rate.
Results:
Detection Rate      : 1.05%
False Positive Rate : 0.98%
Stable alert volume but limited anomaly detection.
12.2 Raw Isolation Forest Detection
Using raw model output without calibration.
Results:
Detection Rate      : 14.39%
False Positive Rate : 14.15%
Higher detection but too many false positives.
13. Feature Importance Analysis
Random Forest analysis identified the most influential behavioral features.
Top features:
hour_deviation
z_logon
session_gap
z_pcs
logon_deviation
device_deviation
device_ratio
burst_score
These features capture temporal, behavioral, and device-based anomalies.
14. Key Observations from V5
Several observations emerged.
Observation 1
Behavioral distributions between normal and injected anomalies still overlap, limiting anomaly separability.
Observation 2
Contextual segmentation (shift + role group) significantly improves peer comparison.
Observation 3
Feature engineering alone cannot fully resolve behavioral overlap.
More advanced clustering methods are needed.
15. Key Achievements of V5
V5 achieved several milestones:
•	Expanded behavioral feature space
•	Integrated HR organizational context
•	Implemented role-group behavioral segmentation
•	Built contextual modeling pipeline (shift + role group)
•	Identified key behavioral indicators
•	Prepared dataset for density-based clustering methods
16. Limitations Identified
The main limitation remains behavioral distribution overlap, which leads to:
•	limited anomaly separability
•	moderate detection performance
Isolation Forest struggles to isolate subtle behavioral deviations.
17. Direction for Next Version
Version 6 will address these limitations using density-based clustering techniques.
Planned approach:
HDBSCAN clustering
This method can:
•	identify dense behavioral clusters
•	detect low-density behavior as anomalies
It is better suited for high-dimensional behavioral datasets.
18. Output of V5
The final output of Version 5 is a feature-complete behavioral dataset containing:
•	behavioral features
•	role group context
•	shift segmentation
Saved as:
behavior_dataset_v5_features.csv
This dataset will serve as the input for Version 6 modeling experiments.
