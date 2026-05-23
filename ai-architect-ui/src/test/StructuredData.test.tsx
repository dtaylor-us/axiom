import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  StructuredDataCard,
  MarkdownExportActions,
  downloadMarkdown,
} from '../components/StructuredData';

describe('StructuredDataCard', () => {
  it('rendersTitleAndFields', () => {
    render(
      <StructuredDataCard
        title="Risk Card"
        fields={[{ label: 'Severity', value: 'high', fieldKey: 'severity' }]}
      />,
    );

    expect(screen.getByText('Risk Card')).toBeInTheDocument();
    expect(screen.getByText('Severity')).toBeInTheDocument();
    expect(screen.getByText('high')).toBeInTheDocument();
  });

  it('rendersSubtitleWhenProvided', () => {
    render(
      <StructuredDataCard
        title="Card"
        subtitle="Optional subtitle"
        fields={[]}
      />,
    );

    expect(screen.getByText('Optional subtitle')).toBeInTheDocument();
  });

  it('rendersDashForEmptyFieldValue', () => {
    render(
      <StructuredDataCard
        title="Card"
        fields={[{ label: 'Empty', value: null, fieldKey: 'empty' }]}
      />,
    );

    // Renders an em-dash span for null/empty values
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('formatsBooleanFieldValues', () => {
    render(
      <StructuredDataCard
        title="Card"
        fields={[
          { label: 'Active', value: true, fieldKey: 'active' },
          { label: 'Archived', value: false, fieldKey: 'archived' },
        ]}
      />,
    );

    expect(screen.getByText('true')).toBeInTheDocument();
    expect(screen.getByText('false')).toBeInTheDocument();
  });
});

describe('downloadMarkdown', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('createsAndClicksDownloadLink', () => {
    const createObjectURL = vi.fn().mockReturnValue('blob:test');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });

    // Mock createElement only for this call — avoids interfering with React render.
    const anchor = { href: '', download: '', click: vi.fn() } as unknown as HTMLAnchorElement;
    vi.spyOn(document, 'createElement').mockReturnValue(anchor);

    downloadMarkdown('my-file.md', '# Content');

    expect(anchor.download).toBe('my-file.md');
    expect(anchor.click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:test');
  });
});

describe('MarkdownExportActions', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });
  it('returnsNullWhenMarkdownIsEmpty', () => {
    const { container } = render(
      <MarkdownExportActions markdown="" markdownFilename="file.md" />,
    );

    expect(container.firstChild).toBeNull();
  });

  it('rendersCompactIconButtons', () => {
    render(
      <MarkdownExportActions
        markdown="# Hello"
        markdownFilename="hello.md"
        compact={true}
      />,
    );

    // Compact mode: copy button + download icon button
    expect(screen.getByLabelText('Download Markdown file')).toBeInTheDocument();
  });

  it('rendersFullButtonsInDefaultMode', () => {
    render(
      <MarkdownExportActions
        markdown="# Hello"
        markdownFilename="hello.md"
        compact={false}
      />,
    );

    expect(screen.getByTitle('Download Markdown file')).toBeInTheDocument();
    expect(screen.getByText('Download .md')).toBeInTheDocument();
  });

  it('triggersDownloadOnDownloadButtonClick', () => {
    render(
      <MarkdownExportActions
        markdown="# Hello"
        markdownFilename="export.md"
        compact={false}
      />,
    );

    // Mock createElement AFTER render so React DOM construction is unaffected.
    const createObjectURL = vi.fn().mockReturnValue('blob:test');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });
    const anchor = { href: '', download: '', click: vi.fn() } as unknown as HTMLAnchorElement;
    vi.spyOn(document, 'createElement').mockReturnValue(anchor);

    fireEvent.click(screen.getByTitle('Download Markdown file'));
    expect(anchor.click).toHaveBeenCalledOnce();
  });

  it('triggersCompactDownloadOnButtonClick', () => {
    render(
      <MarkdownExportActions
        markdown="# Hello"
        markdownFilename="compact.md"
        compact={true}
      />,
    );

    // Mock createElement AFTER render so React DOM construction is unaffected.
    const createObjectURL = vi.fn().mockReturnValue('blob:test');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });
    const anchor = { href: '', download: '', click: vi.fn() } as unknown as HTMLAnchorElement;
    vi.spyOn(document, 'createElement').mockReturnValue(anchor);

    fireEvent.click(screen.getByLabelText('Download Markdown file'));
    expect(anchor.click).toHaveBeenCalledOnce();
  });
});
