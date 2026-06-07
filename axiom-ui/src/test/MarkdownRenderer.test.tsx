import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

describe('MarkdownRenderer', () => {
  it('rendersEmptyState_whenContentIsEmpty', () => {
    render(<MarkdownRenderer content="" />);
    expect(screen.getByTestId('markdown-empty')).toBeInTheDocument();
    expect(screen.getByText('No content available')).toBeInTheDocument();
  });

  it('rendersEmptyState_whenContentIsWhitespace', () => {
    render(<MarkdownRenderer content="   " />);
    expect(screen.getByTestId('markdown-empty')).toBeInTheDocument();
  });

  it('rendersMarkdownContent', () => {
    render(<MarkdownRenderer content="# Hello World" />);
    expect(screen.getByTestId('markdown-content')).toBeInTheDocument();
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });

  it('rendersBoldText', () => {
    render(<MarkdownRenderer content="This is **bold** text" />);
    const bold = screen.getByText('bold');
    expect(bold.tagName.toLowerCase()).toBe('strong');
  });

  it('rendersTableWithGfm', () => {
    const md = '| Name | Value |\n|------|-------|\n| Alpha | 1 |\n';
    render(<MarkdownRenderer content={md} />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Alpha')).toBeInTheDocument();
  });

  it('rendersBlockquote', () => {
    render(<MarkdownRenderer content="> This is a quote" />);
    expect(screen.getByText('This is a quote')).toBeInTheDocument();
  });

  it('rendersCodeBlock', () => {
    render(<MarkdownRenderer content={'```\nconst x = 1;\n```'} />);
    expect(screen.getByText(/const x = 1/)).toBeInTheDocument();
  });

  it('rendersH2Header', () => {
    render(<MarkdownRenderer content="## Section Title" />);
    const h2 = screen.getByRole('heading', { level: 2 });
    expect(h2).toHaveTextContent('Section Title');
  });

  it('rendersH3Header', () => {
    render(<MarkdownRenderer content="### Subsection" />);
    const h3 = screen.getByRole('heading', { level: 3 });
    expect(h3).toHaveTextContent('Subsection');
  });

  it('rendersH4Header', () => {
    render(<MarkdownRenderer content="#### Detail" />);
    const h4 = screen.getByRole('heading', { level: 4 });
    expect(h4).toHaveTextContent('Detail');
  });

  it('rendersHorizontalRule', () => {
    render(<MarkdownRenderer content={'Line one\n\n---\n\nLine two'} />);
    expect(document.querySelector('hr')).toBeInTheDocument();
  });
});
