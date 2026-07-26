ALTER TABLE projects ADD COLUMN user_id UUID;

UPDATE projects
SET user_id = '29ad1dc8-6853-37ac-9e7e-9e1b0d1f661c'
WHERE user_id IS NULL;

ALTER TABLE projects ALTER COLUMN user_id SET NOT NULL;

CREATE INDEX idx_projects_user_status_updated ON projects(user_id, status, updated_at DESC);
