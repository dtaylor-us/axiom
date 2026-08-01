ALTER TABLE review_reports
    ALTER COLUMN recommendation_roadmap TYPE JSONB
    USING CASE
        WHEN recommendation_roadmap IS NULL OR trim(recommendation_roadmap) = '' THEN '[]'::jsonb
        ELSE recommendation_roadmap::jsonb
    END;
