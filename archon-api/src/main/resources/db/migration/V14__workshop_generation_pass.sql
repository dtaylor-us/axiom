-- Track which user-triggered generation pass created or last updated each attribute.

ALTER TABLE workshop_attributes
    ADD COLUMN first_generation_pass INTEGER;

ALTER TABLE workshop_attributes
    ADD COLUMN last_generation_pass INTEGER;
