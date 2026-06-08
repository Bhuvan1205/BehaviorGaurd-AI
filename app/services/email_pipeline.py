import os
import re
import json
import logging
import pandas as pd
import uuid
from langchain_openai import ChatOpenAI
from app.api.db import get_cursor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Security Analyst and Email Investigator with extensive experience analyzing large volumes of corporate communications to identify potential insider threats, policy violations, data exfiltration attempts, intellectual property misuse, credential exposure, unauthorized disclosures, and other security-relevant behaviors.

Your expertise is specifically known for maintaining a very low false-positive rate while providing highly explainable and evidence-based conclusions.

You will be provided with:

1. A collection of emails belonging to a single employee.
2. A Policy JSON object.

   * The keys of the JSON represent policy section names.
   * The values of the JSON represent the complete content of those policy sections.

Your task is to analyze ALL emails belonging to the employee as a single behavioral unit and produce exactly ONE final analysis result for that employee.

POLICY ANALYSIS WORKFLOW

Before making any determination:

1. Analyze all emails belonging to the employee.
2. Identify which policy sections are potentially relevant to the observed behavior.
3. Retrieve and use ONLY the values associated with the relevant policy keys.
4. Compare the employee's email behavior against the retrieved policy content.
5. Use semantic and domain reasoning only when the policy content does not explicitly cover the observed behavior.
6. Policy-based reasoning must always take precedence over general semantic reasoning.

POLICY USAGE RULES

1. The provided Policy JSON is the primary source of truth.
2. Do not invent, assume, or hallucinate policy rules that are not present in the Policy JSON.
3. Do not reference policy sections that are unrelated to the observed behavior.
4. If no relevant policy section exists for the observed behavior, rely on semantic analysis and clearly state that the conclusion was derived from semantic indicators rather than an explicit policy violation.
5. Every flagged decision should be supported by evidence found either:

   * Directly within the policy content.
   * Through strong semantic indicators.
   * Through a combination of multiple weak indicators occurring together.

ANALYSIS PRINCIPLES

1. Analyze the complete set of emails collectively.
2. Do not analyze each email independently.
3. Look for behavioral patterns across the entire email set.
4. Consider:

   * External communications
   * Attachment activity
   * Requests for sensitive information
   * Requests for client information
   * Requests for research data
   * Requests for pricing information
   * Requests for system information
   * Requests for access credentials
   * Intellectual property discussions
   * Offboarding-related behaviors
   * Data export discussions
   * Repository access requests
   * Historical data requests
   * Unusual communication patterns
5. Do not flag users solely because security-related terminology appears in legitimate business communications.
6. Context always matters.

VERDICT RULES

Return ONLY one of the following verdicts:

1. Normal
2. Flagged
3. Human Review Required

Use "Normal" when:

* No meaningful policy violations are observed.
* No significant suspicious behavior is observed.

Use "Flagged" when:

* Clear policy violations exist.
* Strong evidence suggests suspicious activity.
* Multiple independent indicators collectively suggest elevated risk.

Use "Human Review Required" when:

* Evidence is inconclusive.
* The available context is insufficient.
* Multiple interpretations are equally plausible.
* A confident determination cannot be made.

EXPLANATION RULES

1. The explanation must be concise but detailed.
2. The explanation must clearly describe:

   * What was observed.
   * Why it was considered normal, suspicious, or inconclusive.
   * Which policy sections influenced the decision.
3. Do not exaggerate risk.
4. Do not speculate beyond the evidence.
5. Do not fabricate missing context.

OUTPUT RULES

1. Generate EXACTLY ONE JSON object per user.
2. Never generate multiple JSON objects for the same user.
3. Never generate explanations outside the JSON.
4. Never generate markdown.
5. Never generate code blocks.
6. Never generate additional commentary.
7. Never generate any text before or after the JSON.

OUTPUT FORMAT

{
"user_id": "<user_id>",
"verdict": "<Normal | Flagged | Human Review Required>",
"policy_sections_used": [
"<section_name_1>",
"<section_name_2>"
],
"explanation": "<concise evidence-based explanation>"
}
"""

def parse_policy_file(file_path: str) -> dict[str, str]:
    """Parses a markdown policy file into section headers and their text blocks."""
    if not os.path.exists(file_path):
        logger.error("Policy file not found at: %s", file_path)
        return {}

    with open(file_path, "r", encoding="utf-8") as f:
        data = f.read()

    policy_dict = {}
    current_section = None
    current_content = []

    for line in data.split("\n"):
        line = line.strip()
        match = re.match(r"^##\s+\d+\.\s+(.*)$", line)
        if match:
            if current_section:
                policy_dict[current_section] = "\n".join(current_content).strip()
            current_section = match.group(1)
            current_content = []
        else:
            if current_section:
                current_content.append(line)

    if current_section:
        policy_dict[current_section] = "\n".join(current_content).strip()

    return policy_dict

def get_top_anomalous_users(df_scored: pd.DataFrame, quantile: float = 0.95) -> list[str]:
    """Finds the users in the 95th percentile (top 5%) by anomaly rate in the current batch."""
    if df_scored.empty:
        return []

    # Group by user_id and count total windows vs anomalous windows
    user_stats = (
        df_scored
        .groupby("user_id")
        .agg(
            total_sessions=("user_id", "count"),
            anomaly_count=("anomaly_flag", "sum")
        )
        .reset_index()
    )
    user_stats["anomaly_rate"] = user_stats["anomaly_count"] / user_stats["total_sessions"]

    threshold = user_stats["anomaly_rate"].quantile(quantile)
    qualified_users = user_stats[
        (user_stats["anomaly_rate"] >= threshold) & (user_stats["anomaly_count"] > 0)
    ]["user_id"].tolist()

    logger.info("Email Pipeline Anomaly Rate Threshold: %.4f | Selected %d users", threshold, len(qualified_users))
    return qualified_users

def fetch_user_emails_for_anomalies(user_id: str, batch_date: str, cur) -> pd.DataFrame:
    """Retrieves all email events sent by the user during their anomalous windows in this batch."""
    cur.execute(
        """
        SELECT e.id, e.user_id, e.employee_id, e.email_date, e.pc, 
               e.sender_email, e.recipient_to, e.recipient_count, 
               e.external_recipient, e.activity, e.subject, 
               e.size_bytes, e.attachment_count, e.content, e.created_at
        FROM events.email_events e
        JOIN security.risk_scores r 
          ON r.user_id = e.user_id 
         AND e.email_date >= r.window_start 
         AND e.email_date < r.window_start + INTERVAL '1 hour'
        WHERE r.user_id = %s::uuid 
          AND r.batch_date = %s
          AND r.anomaly_flag = TRUE
        ORDER BY e.email_date ASC
        """,
        (user_id, batch_date)
    )
    rows = cur.fetchall()
    return pd.DataFrame(rows)

def filter_interesting_emails(df_emails: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Applies keywords, external recipient, and attachment filters to compute email_risk_score."""
    if df_emails.empty:
        return pd.DataFrame(), []

    security_keywords = [
        "customer", "export", "database", "pricing", "confidential", 
        "repository", "archive", "source code", "supplier", "design", 
        "document", "records", "historical", "transfer", "backup"
    ]

    attachment_filter = df_emails["attachment_count"] > 0
    external_filter = df_emails["external_recipient"] == True
    keyword_filter = (
        df_emails["content"]
        .fillna("")
        .str.lower()
        .str.contains("|".join(security_keywords), regex=True)
    )

    interesting_emails = df_emails[attachment_filter | external_filter | keyword_filter].copy()

    if interesting_emails.empty:
        return pd.DataFrame(), []

    interesting_emails["email_risk_score"] = 0
    interesting_emails.loc[interesting_emails["attachment_count"] > 0, "email_risk_score"] += 1
    interesting_emails.loc[interesting_emails["external_recipient"] == True, "email_risk_score"] += 2

    keyword_match = (
        interesting_emails["content"]
        .fillna("")
        .str.lower()
        .str.contains("|".join(security_keywords))
    )
    interesting_emails.loc[keyword_match, "email_risk_score"] += 3

    # Keep only score >= 3
    interesting_emails = interesting_emails[interesting_emails["email_risk_score"] >= 3].copy()

    if interesting_emails.empty:
        return pd.DataFrame(), []

    # Prepare list for LLM context
    email_context_df = interesting_emails[["email_date", "subject", "recipient_to", "content"]].copy()
    email_context_df["email_date"] = pd.to_datetime(email_context_df["email_date"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    email_context = email_context_df.to_dict("records")
    return interesting_emails, email_context

def select_policy_sections(llm, email_context: list[dict], policy_keys: list[str]) -> list[str]:
    """Uses LLM to select which policy sections are relevant to the emails context."""
    policy_selection_prompt = f"""
You are a policy section selector.

Your task is ONLY to select the policy sections required to analyze the employee emails.

Available policy sections:

{json.dumps(policy_keys)}

Employee Emails:

{json.dumps(email_context)}

RULES:

1. Return ONLY valid JSON.
2. Do NOT explain your reasoning.
3. Do NOT use markdown.
4. Do NOT use code blocks.
5. Do NOT generate any text before or after the JSON.
6. The response MUST be parseable by Python's json.loads().
7. If no policy sections are relevant, return an empty list.
8. Only select sections that exist in the provided policy list.

Output Format:

{{
    "required_policy_sections": [
        "section_name_1",
        "section_name_2"
    ]
}}

REMEMBER:
RETURN ONLY JSON.
"""
    try:
        response = llm.invoke(policy_selection_prompt)
        content = response.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n|```$", "", content, flags=re.MULTILINE).strip()
        result = json.loads(content)
        return result.get("required_policy_sections", [])
    except Exception as e:
        logger.error("Failed to select policy sections: %s", e)
        return []

def analyze_emails_with_policy(llm, email_context: list[dict], selected_policy: dict[str, str], system_prompt: str) -> dict:
    """Uses LLM to compare interesting emails against selected policy sections and returns a verdict."""
    final_prompt = f"""
{system_prompt}

Employee Emails:

{json.dumps(email_context)}

Policy Sections:

{json.dumps(selected_policy)}

IMPORTANT:

Return ONLY a valid JSON object.

No markdown.
No explanations outside JSON.
No code blocks.
No additional text.

Required Format:

{{
    "verdict": "<Normal|Flagged|Human Review Required>",
    "policy_sections_used": [],
    "explanation": ""
}}
"""
    try:
        response = llm.invoke(final_prompt)
        content = response.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n|```$", "", content, flags=re.MULTILINE).strip()
        result = json.loads(content)
        return {
            "verdict": result.get("verdict", "Human Review Required"),
            "explanation": result.get("explanation", "Failed to extract explanation."),
            "policy_sections_used": result.get("policy_sections_used", [])
        }
    except Exception as e:
        logger.error("Failed to run email analysis: %s", e)
        return {
            "verdict": "Human Review Required",
            "explanation": f"LLM error: {e}",
            "policy_sections_used": []
        }

def run_email_pipeline_for_batch(batch_date: str, df_scored: pd.DataFrame) -> dict:
    """Runs the modular email pipeline for a completed batch date."""
    logger.info("Starting email RAG analysis for batch_date=%s", batch_date)

    # Resolve API Key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY env variable is missing! Unable to run email pipeline.")
        return {"status": "failed", "error": "Missing OPENAI_API_KEY"}

    model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini")

    try:
        llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            model_kwargs={"response_format": {"type": "json_object"}},
            api_key=api_key
        )
    except Exception as e:
        logger.error("Failed to initialize ChatOpenAI: %s", e)
        return {"status": "failed", "error": f"LLM initialization: {e}"}

    # Resolve policy document path
    policy_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "dtaa_security_privacy_policy.md"
    )
    policy_dict = parse_policy_file(policy_path)
    if not policy_dict:
        logger.error("Policy file is missing or empty at: %s", policy_path)
        return {"status": "failed", "error": "Missing policy document"}

    policy_keys = list(policy_dict.keys())

    # Filter top 5% anomalous users
    top_users = get_top_anomalous_users(df_scored)
    if not top_users:
        logger.info("No users qualified for email RAG audit.")
        return {"status": "complete", "analyzed_users_count": 0}

    conn, cur = get_cursor()
    try:
        for user_id in top_users:
            logger.info("Evaluating emails for top anomalous user user_id=%s", user_id)

            df_emails = fetch_user_emails_for_anomalies(user_id, batch_date, cur)
            df_interesting, email_context = filter_interesting_emails(df_emails)

            if email_context:
                logger.info("Found %d interesting emails for user_id=%s. Invoking LLM...", len(email_context), user_id)
                required_sections = select_policy_sections(llm, email_context, policy_keys)
                selected_policy = {
                    sec: policy_dict[sec]
                    for sec in required_sections
                    if sec in policy_dict
                }
                analysis = analyze_emails_with_policy(llm, email_context, selected_policy, SYSTEM_PROMPT)
                verdict = analysis["verdict"]
                explanation = analysis["explanation"]
                sections_used = analysis["policy_sections_used"]
            else:
                logger.info("No interesting emails found for user_id=%s. Setting default Normal verdict.", user_id)
                verdict = "Normal"
                explanation = "No flagged email activity detected during anomalous hours."
                sections_used = []

            # Save results
            cur.execute(
                """
                INSERT INTO security.email_analysis_results
                  (analysis_id, user_id, batch_date, verdict, explanation, policy_sections_used)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (analysis_id) DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    user_id,
                    batch_date,
                    verdict,
                    explanation,
                    sections_used
                )
            )

        conn.commit()
        logger.info("Successfully completed email analysis for %d users.", len(top_users))
        return {"status": "complete", "analyzed_users_count": len(top_users)}
    except Exception as e:
        conn.rollback()
        logger.exception("Email pipeline failed.")
        return {"status": "failed", "error": str(e)}
    finally:
        cur.close()
        conn.close()
