interface Message {
  role: 'user' | 'agent';
  content: string;
}

interface Props {
  messages: Message[];
  isLoading?: boolean;
}

export function ConversationThread({ messages, isLoading }: Props) {
  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3" data-testid="conversation-thread">
      {messages.length === 0 && !isLoading && (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-[13px] text-gray-400 text-center max-w-xs">
            Describe the system you are designing. I will ask questions to elicit quality attributes.
          </p>
        </div>
      )}
      {messages.map((msg, idx) => (
        <div
          key={idx}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap ${
              msg.role === 'user'
                ? 'bg-accent text-white'
                : 'bg-white border border-gray-200 text-gray-800'
            }`}
          >
            {msg.content}
          </div>
        </div>
      ))}
      {isLoading && (
        <div className="flex justify-start" aria-label="Agent is thinking" aria-live="polite">
          <div className="bg-white border border-gray-200 rounded-xl px-3.5 py-3">
            <div className="flex gap-1.5 items-center">
              <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.3s]" />
              <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.15s]" />
              <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
