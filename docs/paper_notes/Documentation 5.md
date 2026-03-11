BehaviorGuard-AI
(DOCUMENTATION 5)
BehaviorGuard-AI
Version V4 – Validation & Explainability Phase
Documentation 5 – Extended Experimental Analysis
1. Introduction
Following the development of the shift-aware anomaly detection architecture in Version V3 and the validation framework introduced in Version V4, the next step in the research pipeline was to conduct extended experimental analysis and interpretability evaluation.
The purpose of this phase is to provide deeper insights into the behavior of the anomaly detection system and understand how the model responds to variations in user activity patterns. Since insider threat datasets rarely contain reliable ground truth labels, evaluation relies on synthetic anomaly injection combined with statistical analysis of model outputs.
This documentation focuses on:
•	Detailed model behavior analysis
•	Stability evaluation of anomaly scores
•	Sensitivity analysis of behavioral features
•	Explainability of anomaly predictions
•	Visualization of anomaly score distributions
These experiments provide stronger scientific justification for the system and improve its readiness for research publication.
2. Extended Validation Objectives
The extended validation phase was designed with the following objectives:
•	Model Stability Analysis
Evaluate whether the anomaly detection system produces consistent results across clusters and shifts.
•	Feature Sensitivity Assessment
Analyze how strongly different behavioral features influence anomaly detection.
•	Score Distribution Evaluation
Investigate how anomaly scores differ between normal observations and injected anomalies.
•	Explainability of Predictions
Provide interpretable evidence explaining why certain events are classified as anomalies.
•	Operational Reliability Assessment
Determine whether the system behaves predictably under realistic variations in user behavior.
3. Anomaly Score Behavior Analysis
Isolation Forest produces an anomaly score that indicates how easily a data point can be isolated in the feature space.
Lower scores indicate a higher likelihood of anomalous behavior, while higher scores correspond to normal observations.
To analyze score behavior, the anomaly score distributions for two groups were examined:
•	Normal events
•	Injected anomaly events
Observations
•	Score distributions show significant overlap between normal and anomalous observations.
•	Some injected anomalies receive scores similar to normal events.
•	Only extreme behavioral deviations produce clearly distinguishable anomaly scores.
Interpretation
This behavior indicates that the current feature space does not strongly separate normal and anomalous behaviors, which explains the moderate detection performance observed in V4.
4. Cluster-Level Model Stability
Because the system uses cluster-specific Isolation Forest models, it is important to evaluate whether model performance is consistent across clusters.
Cluster Stability Evaluation
For each cluster, the following metrics were evaluated:
•	Average anomaly score
•	Detection rate
•	False positive rate
Observations
•	Detection rates across clusters remain relatively similar.
•	Clusters with highly homogeneous behavioral profiles show slightly better anomaly detection.
•	Clusters containing diverse behavioral patterns show weaker anomaly separability.

Interpretation
Peer clustering improves contextual anomaly detection, but clusters with highly variable behavior reduce model sensitivity.
5. Shift-Based Detection Stability
BehaviorGuard-AI uses shift-based segmentation to account for time-dependent behavioral patterns.
To validate the effectiveness of this design, anomaly detection performance was analyzed across the three shifts.
Shift	Detection Performance
Day	Strongest detection performance
Evening	Moderate detection performance
Night	Slightly weaker detection
Explanation
Daytime activity tends to follow more structured behavioral patterns, making deviations easier to detect.
Night activity often includes irregular usage patterns, which increases behavioral variance and reduces anomaly separability.
This result confirms that shift-aware behavioral modeling improves contextual understanding of user activity.
6. Feature Influence Analysis
The anomaly detection system relies on several behavioral features derived from logon activity.
Key features used include:
logon_count
logoff_count
unique_pcs
z_logon
z_pcs
To understand the influence of each feature, synthetic anomalies were injected independently across features.
Feature Sensitivity Findings
Feature	Influence on Detection
logon_count	    Moderate
unique_pcs	    Moderate
z_logon	        High
z_pcs	        High
logoff_count	Low
Interpretation
Standardized deviation features (z_logon, z_pcs) provide stronger anomaly signals than raw activity counts.
This suggests that relative deviations from baseline behavior are more informative than absolute activity values.
7. Explainability Analysis
One challenge of unsupervised anomaly detection models is the lack of interpretability.
To improve transparency, anomaly explanations were generated by analyzing feature deviations for detected anomalies.
Example anomaly explanation:
User: U135
Shift: Evening

Observed Behavior:
logon_count = 14
cluster_mean_logon = 4.3
z_logon = +2.8

Interpretation:
User activity significantly exceeded cluster baseline.
Explainability Strategy
For each detected anomaly:
•	Behavioral features are compared against cluster baseline statistics.
•	Standardized deviations (z-scores) are calculated.
•	Features with the largest deviations are identified as potential anomaly drivers.
This approach allows security analysts to understand why an event was flagged, improving system transparency.
8. Operational Alert Behavior
In a real-world deployment, anomaly detection systems must produce manageable alert volumes.
The percentile-based threshold introduced in V3 and evaluated in V4 ensures that the alert rate remains stable.
Alert Volume Behavior
Without calibration:
Alert Rate ≈ 15%
With percentile calibration:
Alert Rate ≈ 1%
This ensures that the system produces a manageable number of alerts for security analysts, reducing alert fatigue.
9. Experimental Limitations
The experiments conducted in Version V4 reveal several limitations:
•	Limited Feature Space
The current feature set primarily captures login behavior and device usage.
Additional contextual features such as:
•	role information
•	department
•	access privilege levels
could improve anomaly detection performance.
•	Synthetic Anomaly Realism
Although synthetic anomalies enable evaluation, they may not fully replicate real insider threat behavior.
Real-world attacks often involve subtle deviations that evolve gradually over time
•	Event-Level Detection Limitations
The current system evaluates anomalies at the individual event level. However, insider threats often manifest through patterns across multiple events, which the current architecture does not fully capture.
10. Summary of V4 Findings
The Version V4 validation experiments produced several important insights:
•	The anomaly detection pipeline is technically stable and operationally viable.
•	Peer clustering provides valuable contextual behavioral comparisons.
•	Percentile calibration ensures manageable alert volumes.
•	Detection sensitivity remains limited due to feature overlap between normal and anomalous behaviors.
•	Shift-based modeling improves contextual anomaly detection.
These findings provide strong scientific justification for the current system design while highlighting areas for improvement.
11. Preparation for Next Phase
The results of Version V4 motivate the next stage of system evolution.
The next version will extend the anomaly detection system by introducing risk-based aggregation and contextual enrichment.
Planned improvements include:
•	User-level risk scoring
•	Temporal aggregation of anomalies
•	Contextual metadata integration
•	Multi-tier alert prioritization
These enhancements will transform BehaviorGuard-AI from a behavioral anomaly detector into a contextual insider threat risk assessment engine.
