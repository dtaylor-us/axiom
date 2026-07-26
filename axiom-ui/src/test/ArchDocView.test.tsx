import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useArchDoc } from '../hooks/useArchDoc';
import { downloadMarkdown } from '../components/StructuredData';
import { ArchDocView } from '../views/ArchDocView';

vi.mock('../hooks/useArchDoc', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../hooks/useArchDoc')>();
  return { ...actual, useArchDoc: vi.fn() };
});
vi.mock('../components/MarkdownRenderer', () => ({
  MarkdownRenderer: ({ content }: { content: string }) => <div data-testid="markdown">{content}</div>,
}));
vi.mock('../components/StructuredData', () => ({
  downloadMarkdown: vi.fn(),
  MarkdownExportActions: ({ markdownFilename }: { markdownFilename: string }) => (
    <span data-testid="tab-export">{markdownFilename}</span>
  ),
}));

const baseData = {
  overviewMarkdown: '# Overview',
  moduleViewMarkdown: '# Modules',
  ccViewMarkdown: '# Connectors',
  allocationViewMarkdown: '# Allocation',
  riskMarkdown: '',
  fullPackageMarkdown: '# Complete package',
  exportFilename: 'architecture-docs-claims.md',
  systemTitle: 'Claims Platform',
  allAdlRules: [
    { rule_id: 'ADL-1', enforcement_level: 'hard' },
    { rule_id: 'ADL-2', validation_hint: { enforcement_level: 'soft' } },
  ],
  loading: false,
  error: null,
  hasData: true,
};

describe('ArchDocView', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useArchDoc).mockReturnValue(baseData as never);
  });

  it('switches document sections and exports the complete package', async () => {
    const user = userEvent.setup();
    render(<ArchDocView />);

    expect(screen.getByText('Claims Platform')).toBeInTheDocument();
    expect(screen.getByText('1 hard ADL rules')).toBeInTheDocument();
    expect(screen.getByTestId('markdown')).toHaveTextContent('# Overview');
    expect(screen.getByTestId('tab-export')).toHaveTextContent('architecture-docs-claims-overview.md');

    const tabs = [
      ['Module View', '# Modules', 'module-view.md'],
      ['Component & Connector', '# Connectors', 'cc-view.md'],
      ['Allocation View', '# Allocation', 'allocation-view.md'],
      ['Risk & Decisions', 'No content available for this section', 'risk.md'],
    ];
    for (const [label, content, filename] of tabs) {
      await user.click(screen.getByRole('button', { name: label }));
      expect(screen.getByText(content)).toBeInTheDocument();
      expect(screen.getByTestId('tab-export')).toHaveTextContent(filename);
    }

    await user.click(screen.getByRole('button', { name: 'Export Arch Docs' }));
    expect(downloadMarkdown).toHaveBeenCalledWith('architecture-docs-claims.md', '# Complete package');
  });

  it.each([
    [{ ...baseData, loading: true }, 'arch-doc-loading'],
    [{ ...baseData, error: 'API unavailable' }, 'arch-doc-error'],
  ])('renders transient states', (data, testId) => {
    vi.mocked(useArchDoc).mockReturnValue(data as never);
    render(<ArchDocView />);
    expect(screen.getByTestId(testId)).toBeInTheDocument();
  });

  it('renders the empty state when no architecture exists', () => {
    vi.mocked(useArchDoc).mockReturnValue({ ...baseData, hasData: false } as never);
    render(<ArchDocView />);
    expect(screen.getByText('No architecture data yet')).toBeInTheDocument();
  });
});
