import { useState, useEffect } from 'react';

const WARN_CHARS = 3_000;

interface Props {
  onSubmit: (input: string) => void;
  disabled?: boolean;
  placeholder?: string;
  /** Pre-fill the textarea (e.g. restored draft). */
  initialValue?: string;
  /** Called whenever the textarea value changes (for external persistence). */
  onValueChange?: (value: string) => void;
}

export function InputPanel({ onSubmit, disabled, placeholder, initialValue, onValueChange }: Props) {
  const [value, setValue] = useState(initialValue ?? '');

  // Sync initialValue into local state when it changes (draft restore).
  useEffect(() => {
    if (initialValue !== undefined) {
      setValue(initialValue);
    }
  }, [initialValue]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    onValueChange?.(e.target.value);
  };

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue('');
    onValueChange?.('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isOverWarnLimit = value.length > WARN_CHARS;

  return (
    <div className="border-t border-gray-200 bg-white p-3" data-testid="input-panel">
      {isOverWarnLimit && (
        <div className="mb-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-1.5 text-[11px] text-amber-700">
          Your message is {value.length.toLocaleString()} characters (recommended: {WARN_CHARS.toLocaleString()} or fewer). Long inputs may reduce response quality — consider splitting into separate messages.
        </div>
      )}
      <div className="flex gap-2 items-end">
        <textarea
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={3}
          placeholder={placeholder ?? 'Describe your system or answer the question above…'}
          className="flex-1 resize-none rounded-xl border border-gray-200 px-3.5 py-2.5 text-[13px] text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-accent/40 disabled:opacity-50"
          data-testid="workshop-input"
          aria-label="Workshop input"
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !value.trim()}
          className="shrink-0 h-10 w-10 rounded-xl bg-accent hover:bg-accent-hover disabled:opacity-40 flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-accent/40"
          data-testid="workshop-submit"
          aria-label="Send"
        >
          <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
      {disabled && (
        <p className="mt-1.5 text-[11px] text-gray-400 text-center">Processing…</p>
      )}
    </div>
  );
}
