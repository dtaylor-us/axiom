package com.archon.api.domain.model;
/**
 * Represents the status of a conversation.
 * 
 * ConversationStatus is an enumeration that defines the possible states
 * a conversation can be in throughout its lifecycle.
 * 
 * @enum ConversationStatus
 * 
 * @constant {ConversationStatus} ACTIVE - Indicates the conversation is currently active and ongoing.
 * @constant {ConversationStatus} COMPLETED - Indicates the conversation has been successfully completed.
 * @constant {ConversationStatus} FAILED - Indicates the conversation has failed or ended unsuccessfully.
 * 
 */
public enum ConversationStatus { ACTIVE, COMPLETED, FAILED }
