import { useCallback } from 'react';
import { useStore } from '../store/useStore';
import { useSSEStream } from './useSSEStream';

/**
 * Hook composing store state + SSE streaming for the chat view.
 */
export function useConversation() {
  const messages = useStore((s) => s.messages);
  const streamingText = useStore((s) => s.streamingText);
  const isStreaming = useStore((s) => s.isStreaming);
  const error = useStore((s) => s.error);
  const stages = useStore((s) => s.stages);
  const conversationId = useStore((s) => s.conversationId);
  const resetConversation = useStore((s) => s.resetConversation);
  const { send, abort, reconnect } = useSSEStream();

  const sendMessage = useCallback(
    async (message: string) => {
      await send(message);
    },
    [send],
  );

  return {
    messages,
    streamingText,
    isStreaming,
    error,
    stages,
    conversationId,
    sendMessage,
    abort,
    reconnect,
    resetConversation,
  };
}
