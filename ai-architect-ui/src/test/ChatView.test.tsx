import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatView } from '../views/ChatView';

/* Mock useConversation */
const mockSendMessage = vi.fn();
const mockAbort = vi.fn();
const mockResetConversation = vi.fn();

let conversationState: Record<string, unknown>;

vi.mock('../hooks/useConversation', () => ({
  useConversation: () => conversationState,
}));

describe('ChatView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    conversationState = {
      messages: [],
      streamingText: '',
      isStreaming: false,
      error: null,
      sendMessage: mockSendMessage,
      abort: mockAbort,
      resetConversation: mockResetConversation,
    };
  });

  it('rendersEmptyWelcomeState', () => {
    render(<ChatView />);
    expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    expect(screen.getByTestId('chat-empty')).toBeInTheDocument();
    expect(screen.getByText('Archon')).toBeInTheDocument();
  });

  it('rendersExamplePromptButtons', () => {
    render(<ChatView />);
    const examples = screen.getAllByTestId('example-prompt');
    expect(examples.length).toBeGreaterThanOrEqual(2);
  });

  it('prefillsInputOnExampleClick', async () => {
    const user = userEvent.setup();
    render(<ChatView />);
    const examples = screen.getAllByTestId('example-prompt');
    await user.click(examples[0]);
    const input = screen.getByTestId('chat-input') as HTMLTextAreaElement;
    expect(input.value.length).toBeGreaterThan(20);
  });

  it('showsConversationAfterSubmit', async () => {
    const user = userEvent.setup();
    render(<ChatView />);
    const input = screen.getByTestId('chat-input');
    await user.type(input, 'Build me a system');
    await user.click(screen.getByTestId('chat-submit'));
    expect(mockSendMessage).toHaveBeenCalledWith('Build me a system');
  });

  it('showsUserMessageAndStreamingText', () => {
    conversationState.messages = [
      { role: 'USER', content: 'Build me a system' },
    ];
    conversationState.isStreaming = true;
    conversationState.streamingText = '**Architecture** analysis';
    render(<ChatView />);
    // When there's streaming text, chat-messages area should render
    expect(screen.getByTestId('chat-messages')).toBeInTheDocument();
    expect(screen.getByTestId('user-message')).toBeInTheDocument();
    expect(screen.getByText('Build me a system')).toBeInTheDocument();
    expect(screen.getAllByTestId('assistant-message').length).toBeGreaterThanOrEqual(1);
  });

  it('rendersError', () => {
    conversationState.messages = [
      { role: 'USER', content: 'hello' },
    ];
    conversationState.error = 'Something went wrong';
    render(<ChatView />);
    expect(screen.getByTestId('chat-error')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('submitButtonDisabledWhenInputEmpty', () => {
    render(<ChatView />);
    expect(screen.getByTestId('chat-submit')).toBeDisabled();
  });

  it('showsAbortButtonWhenStreaming', () => {
    conversationState.isStreaming = true;
    conversationState.streamingText = 'hello';
    render(<ChatView />);
    expect(screen.getByTestId('chat-abort')).toBeInTheDocument();
  });

  it('callsAbortOnStopClick', async () => {
    conversationState.isStreaming = true;
    conversationState.streamingText = 'hello';
    const user = userEvent.setup();
    render(<ChatView />);
    await user.click(screen.getByTestId('chat-abort'));
    expect(mockAbort).toHaveBeenCalled();
  });

  it('callsResetConversation', async () => {
    const user = userEvent.setup();
    render(<ChatView />);
    await user.click(screen.getByTestId('chat-reset'));
    expect(mockResetConversation).toHaveBeenCalled();
  });

  it('disablesInputAndAbortWhenStreaming', () => {
    conversationState.isStreaming = true;
    conversationState.streamingText = 'hello';
    render(<ChatView />);
    expect(screen.getByTestId('chat-input')).toBeDisabled();
  });
});
