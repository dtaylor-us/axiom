package com.archon.api.domain.model;

/**
 * Durable pipeline run status values.
 *
 * <p>Status is independent of the SSE stream: stream loss does not change a run's status.</p>
 */
public enum PipelineRunStatus {
    RUNNING, COMPLETED, FAILED, COMPLETED_WITH_GAPS
}

