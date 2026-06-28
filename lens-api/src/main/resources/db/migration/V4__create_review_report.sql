CREATE TABLE review_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES review_sessions(id),
    executive_summary TEXT,
    azure_waf_scorecard JSONB,
    atam_analysis JSONB,
    sei_analysis JSONB,
    structural_analysis JSONB,
    insufficient_info_gaps JSONB,
    recommendation_roadmap TEXT,
    overall_rating VARCHAR(50),
    generated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE review_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES review_reports(id) ON DELETE CASCADE,
    finding_type VARCHAR(50) NOT NULL,
    category VARCHAR(255),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    evidence TEXT,
    framework_reference VARCHAR(255),
    severity VARCHAR(20) NOT NULL
);

CREATE TABLE review_risks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES review_reports(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    likelihood VARCHAR(20) NOT NULL,
    affected_area VARCHAR(255),
    mitigation_strategy TEXT,
    framework_reference VARCHAR(255)
);
