package com.lens.api.repository;

import com.lens.api.domain.model.GapQuestion;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface GapQuestionRepository extends JpaRepository<GapQuestion, UUID> {

    List<GapQuestion> findBySessionIdOrderByAskedAtAsc(UUID sessionId);

    List<GapQuestion> findBySessionIdAndRoundOrderByAskedAtAsc(UUID sessionId, int round);

    Optional<GapQuestion> findByIdAndSessionId(UUID id, UUID sessionId);

    void deleteBySessionId(UUID sessionId);
}
