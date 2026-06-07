import type { Components } from 'react-markdown';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
}

const components: Components = {
  table: ({ children, ...props }) => (
    <div className="overflow-x-auto my-4 rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm" {...props}>
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead className="bg-gray-50" {...props}>{children}</thead>
  ),
  th: ({ children, ...props }) => (
    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide" {...props}>
      {children}
    </th>
  ),
  td: ({ children, ...props }) => (
    <td className="px-3 py-2 text-gray-700 align-top" {...props}>{children}</td>
  ),
  tr: ({ children, ...props }) => (
    <tr className="border-t border-gray-100 even:bg-gray-50/50" {...props}>
      {children}
    </tr>
  ),
  blockquote: ({ children, ...props }) => (
    <blockquote
      className="border-l-4 border-blue-400/50 bg-blue-50/40 rounded-r-lg pl-4 pr-3 py-2 my-3 text-[13px] text-gray-600 not-italic [&>p]:my-1"
      {...props}
    >
      {children}
    </blockquote>
  ),
  pre: ({ children, ...props }) => (
    <pre
      className="bg-gray-50 border border-gray-200 rounded-lg p-4 overflow-x-auto my-3 text-sm leading-relaxed"
      {...props}
    >
      {children}
    </pre>
  ),
  h2: ({ children, ...props }) => (
    <h2
      className="text-lg font-bold text-gray-800 mt-8 mb-3 pb-1.5 border-b border-gray-200 first:mt-0"
      {...props}
    >
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 className="text-base font-semibold text-gray-800 mt-6 mb-2" {...props}>
      {children}
    </h3>
  ),
  h4: ({ children, ...props }) => (
    <h4 className="text-sm font-semibold text-gray-700 mt-4 mb-1" {...props}>
      {children}
    </h4>
  ),
  hr: (props) => <hr className="my-6 border-gray-200" {...props} />,
};

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content.trim()) {
    return (
      <p className="text-gray-400 italic" data-testid="markdown-empty">
        No content available
      </p>
    );
  }

  return (
    <div
      className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-700 prose-p:leading-relaxed prose-code:text-emerald-700 prose-code:bg-emerald-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:before:content-none prose-code:after:content-none prose-strong:text-gray-800 prose-li:text-gray-700 prose-li:my-0.5"
      data-testid="markdown-content"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
