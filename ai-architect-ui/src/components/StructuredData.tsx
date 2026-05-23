import { CopyButton } from './CopyButton';
import type { ReactNode } from 'react';

type StructuredFieldValue = string | number | boolean | null | undefined;

function formatValue(v: StructuredFieldValue): string {
  if (v === null || v === undefined) return '';
  if (typeof v === 'boolean') return v ? 'true' : 'false';
  return String(v);
}

export function StructuredDataCard({
  title,
  subtitle,
  fields,
  copyValue,
  className = '',
  'data-testid': testId,
}: {
  title: string;
  subtitle?: string;
  fields: { label: string; value: StructuredFieldValue; fieldKey: string }[];
  copyValue?: string;
  className?: string;
  'data-testid'?: string;
}) {
  return (
    <section
      className={`border border-gray-200 rounded-xl bg-white ${className}`}
      data-testid={testId}
      data-structured-card="true"
      data-title={title}
    >
      <div className="px-4 py-3 border-b border-gray-100 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-gray-900 truncate">{title}</h2>
          {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        {copyValue && (
          <CopyButton
            text={copyValue}
            label="Copy"
            title="Copy structured data"
            className="shrink-0"
          />
        )}
      </div>
      <div className="px-4 py-3">
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3">
          {fields.map((f) => (
            <div key={f.fieldKey} data-field={f.fieldKey}>
              <dt className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">
                {f.label}
              </dt>
              <dd className="mt-1 text-sm text-gray-800 break-words">
                {formatValue(f.value) || <span className="text-gray-400">—</span>}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

function downloadJson(filename: string, json: unknown) {
  const content = JSON.stringify(json, null, 2);
  const blob = new Blob([content], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function StructuredExportBar({
  title,
  json,
  filename,
  extraRight,
}: {
  title: string;
  json: unknown;
  filename: string;
  extraRight?: ReactNode;
}) {
  const jsonString = JSON.stringify(json, null, 2);
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-gray-100">
      <h1 className="text-base font-semibold text-gray-800">{title}</h1>
      <div className="flex items-center gap-2">
        {extraRight}
        <CopyButton
          text={jsonString}
          label="Copy JSON"
          title="Copy as JSON"
        />
        <button
          type="button"
          onClick={() => downloadJson(filename, json)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors"
          title="Download JSON file"
        >
          <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 2v8M5 7l3 3 3-3M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1" />
          </svg>
          Download .json
        </button>
      </div>
    </div>
  );
}

