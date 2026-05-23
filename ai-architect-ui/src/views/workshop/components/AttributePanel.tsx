import { useMemo } from 'react';
import type { QualityAttribute } from '../../../types/workshop';
import { MarkdownExportActions } from '../../../components/StructuredData';
import { AttributeCard } from './AttributeCard';
import { buildQualityAttributesMarkdown } from '../workshopMarkdown';

function countByConfidence(attrs: QualityAttribute[]) {
  let confirmed = 0;
  let inferred = 0;
  let tentative = 0;
  for (const a of attrs) {
    if (a.confidence === 'confirmed') confirmed += 1;
    else if (a.confidence === 'inferred') inferred += 1;
    else tentative += 1;
  }
  return { confirmed, inferred, tentative };
}

interface Props {
  attributes: QualityAttribute[];
  /** Used for export filenames when attributes exist. */
  sessionId: string | null;
  /** Shown in Markdown export header. */
  systemName: string;
  /** Narrow screens: icon-only export controls. */
  compactToolbar?: boolean;
  hasSufficientAttributes: boolean;
  onSendToPipeline: () => void;
  sendingToPipeline: boolean;
  generationCount: number;
  sessionAttributesStale: boolean;
}

export function AttributePanel({
  attributes,
  sessionId,
  systemName,
  compactToolbar = false,
  hasSufficientAttributes,
  onSendToPipeline,
  sendingToPipeline,
  generationCount,
  sessionAttributesStale,
}: Props) {
  const { confirmed, inferred, tentative } = countByConfidence(attributes);
  const totalOpenQuestions = attributes.reduce(
    (sum, a) => sum + (a.openQuestions?.length ?? 0),
    0,
  );
  const totalResolvedQuestions = attributes.reduce(
    (sum, a) => sum + (a.questionsResolvedCount ?? 0),
    0,
  );
  const title =
    generationCount > 0
      ? `Quality attributes — Pass ${generationCount}`
      : 'Quality attributes — Not yet generated';

  const attributesMarkdown = useMemo(
    () =>
      attributes.length > 0 && sessionId
        ? buildQualityAttributesMarkdown(attributes, {
            systemName: systemName.trim() || undefined,
            sessionId,
          })
        : '',
    [attributes, sessionId, systemName],
  );

  return (
    <div className="flex flex-col h-full" data-testid="attribute-panel">
      <div className="px-3 sm:px-4 py-3 border-b border-gray-200">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-2">
          <p className="text-[12px] font-semibold text-gray-700 uppercase tracking-wide min-w-0">
            {title}
          </p>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 sm:justify-end sm:shrink-0">
            {attributes.length > 0 && sessionId && (
              <div data-testid="attribute-markdown-export" className="min-w-0">
                <MarkdownExportActions
                  markdown={attributesMarkdown}
                  markdownFilename={`workshop-quality-attributes-${sessionId}.md`}
                  compact={compactToolbar}
                />
              </div>
            )}
            <span className="text-[11px] text-gray-500 whitespace-nowrap">{attributes.length} elicited</span>
          </div>
        </div>
        {generationCount > 0 && (
          <p className="text-[11px] text-gray-500 mt-1">
            {confirmed} confirmed · {inferred} inferred · {tentative} tentative
          </p>
        )}
        <p className="text-[11px] text-gray-500 mt-1">
          {totalResolvedQuestions} questions resolved · {totalOpenQuestions} still open
        </p>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-2.5 sm:p-3 flex flex-col gap-2">
        {attributes.length === 0 && (
          <p className="text-[12px] text-gray-400 text-center mt-8">
            Attributes will appear here as they are elicited.
          </p>
        )}
        {attributes.map((attr) => (
          <AttributeCard
            key={attr.attributeId}
            attribute={attr}
            sessionAttributesStale={sessionAttributesStale}
          />
        ))}
      </div>

      {hasSufficientAttributes && (
        <div className="border-t border-gray-200 p-3 bg-emerald-50/50">
          <p className="text-[12px] text-emerald-700 mb-2">
            Sufficient attributes elicited. Ready to generate architecture.
          </p>
          <button
            onClick={onSendToPipeline}
            disabled={sendingToPipeline}
            className="w-full bg-accent hover:bg-accent-hover disabled:opacity-50 text-white rounded-xl py-2.5 text-[13px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent/40"
            data-testid="send-to-pipeline-btn"
          >
            {sendingToPipeline ? 'Sending…' : 'Send to Pipeline →'}
          </button>
        </div>
      )}
    </div>
  );
}
