-- =====================================================
-- BehaviorGuard-AI
-- Milestone 6: Email Analysis RAG Results Storage
-- =====================================================

CREATE TABLE IF NOT EXISTS security.email_analysis_results (
    analysis_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
    batch_date DATE NOT NULL,
    verdict VARCHAR(50) NOT NULL, -- 'Normal', 'Flagged', 'Human Review Required'
    explanation TEXT NOT NULL,
    policy_sections_used TEXT[], -- array of policy section headers
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_analysis_user_batch 
ON security.email_analysis_results(user_id, batch_date DESC);
