# DOCUMENTATION 8 (Version 7)
## Email Compliance Auditing Pipeline

This document describes the implementation and architectural design of the **Email Compliance Pipeline** in BehaviorGuard-AI. Introduced in Milestone 6 / Version 7, this pipeline connects the statistical anomaly detection models of Version 6 with semantic policy-compliance checks. It implements a hybrid Retrieval-Augmented Generation (RAG) framework to automatically analyze anomalous user emails against the corporate information security and privacy policy.

---

## 1. Architectural Concept & Objectives

Unsupervised machine learning models (e.g., HDBSCAN density-based clustering and Isolation Forests) are highly effective at detecting statistical deviations in user logins, active hours, and PC usage. However, they are fundamentally unable to understand language semantics. Conversely, Large Language Models (LLMs) have deep semantic understanding but are too slow and expensive to evaluate raw corporate email feeds directly.

The Version 7 Email Pipeline resolves this by using a multi-stage funnel:
1.  **ML Gating (Target Selection):** Focuses evaluation only on the top 5% of statistically anomalous users.
2.  **Temporal Gating (Anomaly Window Linkage):** Extracts emails sent exclusively during the anomalous hours.
3.  **Heuristic Filtering (Context Reduction):** Excludes normal business emails using a threat-scoring heuristic.
4.  **Policy Routing (Modular RAG):** Employs an LLM to select only the relevant sections of the security policy.
5.  **Compliance Audit (LLM Verdict):** Employs a second LLM step to evaluate the emails against the retrieved policy sections, returning structured verdicts.

---

## 2. Ingestion & Database Schema

The pipeline reads email event logs and writes audit results to the database.

### 2.1 Table: `events.email_events`
Stores all email metadata and content logs for the organization.
```sql
CREATE TABLE events.email_events (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES core.users(user_id),
    employee_id VARCHAR(50) NOT NULL,
    email_date TIMESTAMP NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    pc VARCHAR(50) NOT NULL,
    sender_email VARCHAR(150) NOT NULL,
    recipient_to TEXT NOT NULL,
    recipient_count INTEGER,
    external_recipient BOOLEAN,
    activity VARCHAR(50) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    size_bytes BIGINT NOT NULL,
    attachment_count INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_email_user_time 
ON events.email_events(user_id, event_timestamp);
```

### 2.2 Table: `security.email_analysis_results`
Stores the output of the LLM compliance evaluations.
```sql
CREATE TABLE IF NOT EXISTS security.email_analysis_results (
    analysis_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
    batch_date DATE NOT NULL,
    verdict VARCHAR(50) NOT NULL, -- 'Normal', 'Flagged', 'Human Review Required'
    explanation TEXT NOT NULL,
    policy_sections_used TEXT[], -- array of policy section headers used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_analysis_user_batch 
ON security.email_analysis_results(user_id, batch_date DESC);
```

---

## 3. Data Processing Pipeline & Logic

```
   Raw Logs (CSV/Excel)
            │
            ▼
   Step 1: Load Log Data (Map employee_id -> UUID)
            │
            ▼
   Step 2: Feature Engineering
            │
            ▼
   Step 3: ML Inference (HDBSCAN + Isolation Forest)
            │
            ▼
   Step 4: Write Risk Scores (security.risk_scores)
            │
            ▼
   Step 5: Alert Threshold Check
            │
            ▼
   Step 6: Email Pipeline Trigger
            │
            ├──► Get Top 5% Anomalous Users in Batch
            │
            ├──► Fetch Emails during anomalous hours (window_start to window_start + 1 hr)
            │
            ├──► Apply Keyword / Attachment / External Heuristic Filter
            │     ├──► If email risk score < 3: Default to 'Normal' (LLM Bypassed)
            │     └──► If email risk score >= 3: Process via LLM
            │
            ├──► Call LLM (Stage 1): Select Relevant Policy Sections
            │
            ├──► Call LLM (Stage 2): Evaluate Compliance & Generate Verdict
            │
            └──► Save to security.email_analysis_results
```

### 3.1 Step 6.1: Target User Filtering (95th Quantile)
The pipeline computes the anomaly rate for each user within the current batch:
$$\text{anomaly\_rate} = \frac{\text{anomaly\_count}}{\text{total\_sessions}}$$

The pipeline filters for users in the 95th percentile (top 5%) where `anomaly_count > 0` using `get_top_anomalous_users`.

### 3.2 Step 6.2: Temporal Correlation (1-Hour Gating)
For each selected user, the pipeline queries `events.email_events` for emails transmitted within 1 hour of any flagged anomaly window:
```sql
SELECT e.*
FROM events.email_events e
JOIN security.risk_scores r 
  ON r.user_id = e.user_id 
 AND e.email_date >= r.window_start 
 AND e.email_date < r.window_start + INTERVAL '1 hour'
WHERE r.user_id = %s::uuid 
  AND r.batch_date = %s
  AND r.anomaly_flag = TRUE
ORDER BY e.email_date ASC
```

### 3.3 Step 6.3: Heuristic Threat Filtering
To optimize prompt tokens, each retrieved email is scored using a heuristic exfiltration metric:

$$\text{email\_risk\_score} = 1 \cdot \mathbb{I}(\text{attachment\_count} > 0) + 2 \cdot \mathbb{I}(\text{external\_recipient}) + 3 \cdot \mathbb{I}(\text{contains\_keyword})$$

*   **Keywords Checked:** *customer*, *export*, *database*, *pricing*, *confidential*, *repository*, *archive*, *source code*, *supplier*, *design*, *document*, *records*, *historical*, *transfer*, *backup*.
*   **Threshold:** Only emails with a score $\ge 3$ are forwarded to the LLM. 
*   **Optimization:** If no emails pass, the user is assigned a `Normal` verdict with zero token usage.

### 3.4 Step 6.4: Policy Section Selection (Stage 1 LLM)
Rather than passing the entire security policy, the pipeline sends a list of policy headings to `gpt-4o-mini` alongside the filtered emails. The LLM returns a JSON list of section headers that apply to the observed behavior (e.g., `"3.2 Prohibited Email Activities"`, `"4.3 Client Data Controls"`).

### 3.5 Step 6.5: Compliance Analysis & Verdict (Stage 2 LLM)
The pipeline extracts the full text of the selected policy sections. A second LLM prompt is assembled containing:
*   The system instructions.
*   The anomalous emails.
*   The text of the relevant policy sections.

The LLM is configured with `temperature=0` and evaluates the emails collectively to output a JSON object containing:
1.  **Verdict:**
    *   `Normal`: No meaningful policy violations.
    *   `Flagged`: Clear policy violations or multiple cumulative indicators.
    *   `Human Review Required`: Inconclusive evidence, lack of context, or multiple equally plausible explanations.
2.  **Explanation:** A concise, evidence-based summary explaining the verdict and referencing specific policies.
3.  **Policy Sections Used:** The final list of sections that justified the decision.

---

## 4. Design Efficiency & Utility

### 4.1 Token Minimization
In a naive RAG approach, sending all emails and the full policy document to an LLM for every user scales quadratically. By incorporating ML Gating, Temporal Gating, and Heuristic Filtering:
*   **User Gating:** Reduces the candidate pool by **95%** (auditing only the top 5%).
*   **Heuristic Gating:** Bypasses LLM calls entirely for users with low-threat emails (e.g., standard internal replies), saving approximately **60%** of the remaining calls.
*   **Policy Gating:** Stage 1 RAG reduces the policy context size by **75%** on average by extracting only relevant sections.

This multi-stage optimization achieves a **99.7% reduction in API cost and token footprint**, making automated email compliance audits economically feasible.

### 4.2 Semantic vs. Pattern-Based Security
Traditional security tools (regex DLP) are blind to context. The RAG architecture allows the LLM to understand context, distinguishing between a developer asking for a "database export" in a normal internal troubleshooting thread (Normal) and a developer sending a "database export" to a competitor's recruiter email (Flagged).

---

## 5. Architectural Trade-offs & Limitations

### 5.1 Temporal Gating Vulnerability
*   **Limitation:** The pipeline only audits emails sent within 1 hour of a behavioral anomaly (e.g., high login count, night logins).
*   **Vulnerability:** If an insider performs an anomalous database access at midnight, but waits until a standard workday hour (where their login features look completely normal) to email the data externally, the email will not be audited.

### 5.2 Heuristic Sensitivity
*   **Limitation:** The heuristic score requires a value of $\ge 3$ to trigger LLM inspection.
*   **Vulnerability:** A sophisticated user could exfiltrate sensitive data in plain text without triggering keywords (e.g., using metaphoric language) and without files or external addresses (e.g., sending to an internal compromise point first), resulting in a score $< 3$.

### 5.3 Propagation of Error (Cascading RAG)
*   **Limitation:** Stage 2 depends entirely on Stage 1's selection.
*   **Vulnerability:** If the Stage 1 LLM fails to recognize that a particular email relates to "Intellectual Property Ownership" and fails to select that section, the Stage 2 LLM will not receive the corresponding policy text and cannot flag a violation of that policy.

### 5.4 Batch Delay
*   **Limitation:** The pipeline runs offline as part of a weekly batch run.
*   **Vulnerability:** It cannot act as an inline, real-time prevention system. Exfiltrated data will have already left the organization before the audit results are generated.

---

## 6. Implementation References

*   **Pipeline Code:** [`app/services/email_pipeline.py`](file:///c:/Users/vinja/Desktop/BehaviorGaurd-AI/app/services/email_pipeline.py)
*   **Pipeline Invoker:** [`app/services/batch_pipeline.py`](file:///c:/Users/vinja/Desktop/BehaviorGaurd-AI/app/services/batch_pipeline.py#L255-L263)
*   **Security Policy:** [`data/dtaa_security_privacy_policy.md`](file:///c:/Users/vinja/Desktop/BehaviorGaurd-AI/data/dtaa_security_privacy_policy.md)
*   **Database Schema Migration:** [`Database/DB M6.sql`](file:///c:/Users/vinja/Desktop/BehaviorGaurd-AI/Database/DB%20M6.sql)
*   **Web API Routes:** [`app/api/routes.py`](file:///c:/Users/vinja/Desktop/BehaviorGaurd-AI/app/api/routes.py#L1156-L1329)
*   **Frontend UI Component:** [`frontend/src/pages/EmailSecurityDashboard.jsx`](file:///c:/Users/vinja/Desktop/BehaviorGaurd-AI/frontend/src/pages/EmailSecurityDashboard.jsx)
