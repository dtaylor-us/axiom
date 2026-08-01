ALTER TABLE architecture_decisions
    ADD COLUMN source_memory_entry_id UUID REFERENCES memory_entries(id);

CREATE INDEX idx_memory_type ON memory_entries(memory_type);
CREATE INDEX idx_memory_tier ON memory_entries(tier);
CREATE INDEX idx_memory_source_pillar ON memory_entries(source_pillar);
CREATE INDEX idx_memory_created_at ON memory_entries(created_at);
CREATE INDEX idx_memory_tags ON memory_entries USING GIN(tags);
CREATE INDEX idx_adrs_status ON architecture_decisions(status);
CREATE INDEX idx_adrs_source_memory ON architecture_decisions(source_memory_entry_id);
