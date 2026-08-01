CREATE TABLE distillation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    session_count INTEGER NOT NULL DEFAULT 0,
    total_candidates INTEGER NOT NULL DEFAULT 0,
    total_persisted INTEGER NOT NULL DEFAULT 0,
    total_superseded INTEGER NOT NULL DEFAULT 0,
    total_conflicts INTEGER NOT NULL DEFAULT 0,
    session_results JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_distillation_jobs_project
    ON distillation_jobs(project_id);
CREATE INDEX idx_distillation_jobs_status
    ON distillation_jobs(status);
