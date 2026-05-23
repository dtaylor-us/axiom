import { useState } from 'react';

interface CopyButtonProps {
  /** Text to write to the clipboard */
  text: string;
  /** Optional visible label shown beside the icon */
  label?: string;
  className?: string;
  title?: string;
}

/**
 * Inline clipboard copy button.
 * Shows a clipboard icon that briefly swaps to a checkmark on success.
 */
export function CopyButton({ text, label, className = '', title = 'Copy to clipboard' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard unavailable – silently ignore */
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={copied ? 'Copied!' : title}
      aria-label={copied ? 'Copied!' : title}
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${className}`}
    >
      {copied ? (
        <svg className="w-3.5 h-3.5 text-emerald-500 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 8l3.5 3.5L13 5" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="5" y="5" width="8" height="9" rx="1" />
          <path d="M3 11V3a1 1 0 011-1h7" />
        </svg>
      )}
      {label && (
        <span className="text-xs font-medium">{copied ? 'Copied!' : label}</span>
      )}
    </button>
  );
}
