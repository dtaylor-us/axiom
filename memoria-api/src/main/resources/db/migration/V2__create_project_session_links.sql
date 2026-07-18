CREATE TABLE project_session_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    pillar VARCHAR(50) NOT NULL,
    session_id UUID NOT NULL,
    linked_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(pillar, session_id)
);
CREATE INDEX idx_session_links_project ON project_session_links(project_id);
