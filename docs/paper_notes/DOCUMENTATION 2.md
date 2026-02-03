DOCUMENTATION 2 (Version 1)
(Logon Behavior Analysis and Statistical Anomaly Modelling)

Project Overview (V1):
BehaviorGuard-AI Version 1 extends the foundational contextual risk modeling established in Version 0 by introducing behavioral analysis based on system logon activity. While V0 focuses on who the user is, V1 emphasizes how the user behaves during system access.
This phase analyzes large-scale authentication logs to identify deviations from normal user behavior that may indicate potential insider threats. The objective is to convert raw system events into structured behavioral patterns and quantify abnormal activity using statistical techniques.
The V1 implementation forms the first dynamic behavioral layer of the UEBA pipeline and is designed to integrate seamlessly with the contextual risk scores developed earlier.
Problem Identification:
Context-aware risk scoring alone is insufficient to detect insider threats, as even high-risk users may behave normally for extended periods, while low-risk users may suddenly exhibit suspicious behavior.
Raw system log data, such as login and logout events, is high-volume and unstructured, making it unsuitable for direct analysis. Additionally, simple threshold-based monitoring fails to capture individual behavioral baselines, leading to excessive false positives.
There is a need for a behavioral modeling approach that can:
•	Learn normal login behavior on a per-user basis
•	Capture temporal and device-usage patterns
•	Quantify deviations in a statistically meaningful manner
Motivation:
System logon behavior is one of the strongest indicators of insider activity, as it reflects when, how often, and from which devices a user accesses organizational resources.
The motivation behind Version 1 is to:
•	Understand how behavioral baselines are constructed in real UEBA systems
•	Learn large-scale log processing and aggregation techniques
•	Bridge the gap between raw security logs and anomaly detection models
This phase emphasizes explainability and statistical rigor, ensuring that anomalous behavior can be clearly interpreted and validated.
Project Scope (Version 1):
The scope of Version 1 focuses on offline behavioral modeling using historical logon data. The following components are included:
•	Large-scale preprocessing of authentication logs
•	Time-window–based aggregation of user activity
•	Construction of per-user behavioral baselines
•	Statistical deviation analysis using normalization techniques
•	Development of a rule-based behavioral risk score
Real-time monitoring, supervised classification, and automated alerting mechanisms are intentionally excluded from this phase and are planned for future versions.
Dataset Description and Preprocessing:
The primary dataset used in this phase is logon.csv, consisting of approximately 3.5 million system logon records. Each record captures authentication-related events with attributes such as user identity, timestamp, device, and activity type.
Key preprocessing steps include:
•	Loading the dataset into a structured Pandas DataFrame
•	Converting timestamp fields into datetime format
•	Verifying data integrity by checking for missing values and duplicates
•	Creating filtered subsets for testing and validation
These steps ensure that the dataset is clean, consistent, and suitable for behavioral analysis.
Behavioral Feature Engineering:
To transform raw log events into meaningful behavioral signals, logon activity was aggregated into fixed hourly time windows for each user.
For every user-hour combination, the following features were computed:
•	Number of logon events
•	Number of logoff events
•	Count of unique devices accessed
This aggregation converts low-level system events into interpretable behavioral patterns that reflect user activity intensity and device usage behavior.
Baseline Behavior Modeling:
User behavior varies significantly across individuals; therefore, global thresholds are ineffective. To address this, per-user statistical baselines were constructed.
For each user, the following baseline metrics were calculated:
•	Mean and standard deviation of logon frequency
•	Mean and standard deviation of device usage
These baselines represent normal behavioral ranges and serve as reference points for detecting abnormal deviations.
Temporal Pattern Analysis:
Temporal characteristics play a critical role in behavioral security analytics. Login timestamps were decomposed to extract the hour of the day, enabling analysis of time-based behavior.
The analysis revealed strong diurnal patterns:
•	Increased activity during morning and evening hours
•	Reduced activity during afternoon hours
•	Rare activity during late-night periods
Such temporal patterns provide essential context, as login activity occurring at unusual hours may indicate elevated risk.
Deviation Analysis Using Z-Scores:
To quantify behavioral abnormalities in user logon activity, statistical normalization was performed using Z-score computation. Deviation metrics were calculated for both logon frequency and device usage in order to measure variations from established per-user behavioral baselines. Since certain users exhibit highly consistent behavior, zero-variance cases were addressed by introducing a small constant to ensure numerical stability and avoid undefined values. The resulting Z-scores represent the extent to which observed behavior deviates from a user’s normal activity patterns in standardized units, enabling meaningful comparison across different users and time windows.
Behavioral Risk Scoring Mechanism:
An initial rule-based behavioral risk scoring mechanism was developed by combining multiple behavioral indicators, including deviations in logon frequency, anomalies in device usage, and login activity occurring during unusual time periods. The resulting risk scores follow a long-tailed distribution, where the majority of records correspond to normal user behavior while a small subset exhibits extreme deviations indicative of potential anomalies. To ensure the validity of the scoring approach, high-risk instances were manually inspected and found to represent plausible behavioral irregularities. This rule-based scoring mechanism establishes an interpretable behavioral risk layer and serves as a foundational precursor to machine learning based anomaly detection techniques planned for subsequent phases of the project.
Multi-Scale Detection Framework (Conceptual):
To support comprehensive threat detection, a multi-resolution behavioral analysis framework was conceptually designed.
The framework includes:
•	Hourly analysis for sudden behavioral spikes
•	Daily aggregation for short-term trend detection
•	Weekly aggregation for identifying gradual behavioral drift
Hierarchical aggregation of these scores enables detection of both abrupt and slow-moving insider threats.
Project Status (After Version 1):
At the completion of Version 1, the following milestones have been achieved:
•	Successful transformation of raw authentication logs into structured behavioral features
•	Construction of individualized behavioral baselines
•	Implementation of statistical deviation metrics
•	Development of an interpretable behavioral risk scoring mechanism
•	Identification of meaningful temporal and device-usage patterns
The behavioral modeling pipeline is now operational and ready for integration with machine learning models in subsequent versions.
Future Direction:
Future versions of BehaviorGuard-AI will build upon the behavioral foundation established in Version 1 by incorporating unsupervised anomaly detection algorithms, contextual risk fusion, and multi-log correlation. These enhancements aim to produce a robust, scalable, and context-aware insider threat detection system aligned with real-world UEBA architectures.


Conclusion:
This documentation describes the design and implementation of the behavioral analysis layer in BehaviorGuard-AI. By systematically modeling user logon behavior and quantifying deviations from established baselines, Version 1 introduces dynamic risk signals that significantly enhance insider threat detection capabilities. This phase establishes a critical bridge between contextual profiling and advanced machine learning–based security analytics.


