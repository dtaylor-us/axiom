package com.archon.api.domain.repository;

import com.archon.api.domain.model.ArchitectureTactic;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface TacticRepository extends JpaRepository<ArchitectureTactic, UUID> {

    List<ArchitectureTactic> findByConversationIdOrderByPriorityAscTacticNameAsc(
            UUID conversationId);

    List<ArchitectureTactic> findByConversationIdAndCharacteristicNameOrderByPriorityAsc(
            UUID conversationId, String characteristicName);

    List<ArchitectureTactic> findByConversationIdAndPriorityOrderByTacticNameAsc(
            UUID conversationId, String priority);

    List<ArchitectureTactic> findByConversationIdAndAlreadyAddressedFalseOrderByPriorityAscTacticNameAsc(
            UUID conversationId);
}
