WITH ranked_reports AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY session_id
            ORDER BY generated_at DESC, id DESC
        ) AS report_rank
    FROM review_reports
)
DELETE FROM review_reports
WHERE id IN (
    SELECT id
    FROM ranked_reports
    WHERE report_rank > 1
);

ALTER TABLE review_reports
    ADD CONSTRAINT review_reports_session_id_unique UNIQUE (session_id);
