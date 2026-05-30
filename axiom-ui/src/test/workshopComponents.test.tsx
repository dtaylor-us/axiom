import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConversationThread } from '../views/workshop/components/ConversationThread';
import { InputPanel } from '../views/workshop/components/InputPanel';
import { GeneratePanel } from '../views/workshop/components/GeneratePanel';

// ─── ConversationThread ───────────────────────────────────────────────────────

describe('ConversationThread', () => {
  it('rendersEmptyStatePromptWhenNoMessages', () => {
    render(<ConversationThread messages={[]} />);
    expect(screen.getByText(/Describe the system/)).toBeInTheDocument();
  });

  it('doesNotRenderEmptyStateWhenLoading', () => {
    render(<ConversationThread messages={[]} isLoading />);
    expect(screen.queryByText(/Describe the system/)).not.toBeInTheDocument();
  });

  it('rendersUserAndAgentMessages', () => {
    render(<ConversationThread messages={[
      { role: 'user', content: 'Hello agent' },
      { role: 'agent', content: 'Hello user' },
    ]} />);
    expect(screen.getByText('Hello agent')).toBeInTheDocument();
    expect(screen.getByText('Hello user')).toBeInTheDocument();
  });

  it('hidesEmptyStateWhenMessagesPresent', () => {
    render(<ConversationThread messages={[{ role: 'user', content: 'Hi' }]} />);
    expect(screen.queryByText(/Describe the system/)).not.toBeInTheDocument();
  });
});

// ─── InputPanel ──────────────────────────────────────────────────────────────

describe('InputPanel', () => {
  it('rendersTextareaAndSubmitButton', () => {
    render(<InputPanel onSubmit={vi.fn()} />);
    expect(screen.getByTestId('input-panel')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('callsOnSubmitWithTrimmedInput', () => {
    const onSubmit = vi.fn();
    render(<InputPanel onSubmit={onSubmit} />);
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: '  Hello world  ' } });
    fireEvent.click(screen.getByRole('button'));
    expect(onSubmit).toHaveBeenCalledWith('Hello world');
  });

  it('doesNotSubmitWhenDisabled', () => {
    const onSubmit = vi.fn();
    render(<InputPanel onSubmit={onSubmit} disabled />);
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'Test input' } });
    fireEvent.click(screen.getByRole('button'));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('doesNotSubmitWhenInputIsEmpty', () => {
    const onSubmit = vi.fn();
    render(<InputPanel onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('clearsInputAfterSubmit', () => {
    render(<InputPanel onSubmit={vi.fn()} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'Some text' } });
    fireEvent.click(screen.getByRole('button'));
    expect(textarea.value).toBe('');
  });

  it('submitsOnEnterKeyWithoutShift', () => {
    const onSubmit = vi.fn();
    render(<InputPanel onSubmit={onSubmit} />);
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
    expect(onSubmit).toHaveBeenCalledWith('Hello');
  });

  it('doesNotSubmitOnShiftEnter', () => {
    const onSubmit = vi.fn();
    render(<InputPanel onSubmit={onSubmit} />);
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('callsOnValueChangeOnEveryKeystroke', () => {
    const onValueChange = vi.fn();
    render(<InputPanel onSubmit={vi.fn()} onValueChange={onValueChange} />);
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'Draft' } });
    expect(onValueChange).toHaveBeenCalledWith('Draft');
  });

  it('showsCharacterWarningOver3000Chars', () => {
    render(<InputPanel onSubmit={vi.fn()} />);
    const longText = 'x'.repeat(3001);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: longText } });
    expect(screen.getByText(/characters.*recommended/)).toBeInTheDocument();
  });

  it('populatesTextareaWithInitialValue', () => {
    render(<InputPanel onSubmit={vi.fn()} initialValue="Pre-filled" />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    expect(textarea.value).toBe('Pre-filled');
  });
});

// ─── GeneratePanel ────────────────────────────────────────────────────────────

describe('GeneratePanel', () => {
  const baseProps = {
    turnComplete: true,
    generationCount: 0,
    attributesStale: false,
    previewLoading: false,
    generateLoading: false,
    onPreview: vi.fn(),
    onGenerate: vi.fn(),
  };

  it('returnsNullWhenTurnNotComplete', () => {
    const { container } = render(<GeneratePanel {...baseProps} turnComplete={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('rendersInitialStateWithReadyToGenerate', () => {
    render(<GeneratePanel {...baseProps} />);
    expect(screen.getByText('Ready to generate?')).toBeInTheDocument();
  });

  it('rendersStateAWithFirstGenerationPrompt', () => {
    render(<GeneratePanel {...baseProps} generationCount={0} />);
    expect(screen.getByText(/Generate quality attributes/)).toBeInTheDocument();
  });

  it('rendersStaleBannerWhenAttributesStale', () => {
    render(<GeneratePanel {...baseProps} generationCount={1} attributesStale />);
    expect(screen.getByText(/New context available/)).toBeInTheDocument();
  });

  it('rendersCompletedBannerAfterFirstGeneration', () => {
    render(<GeneratePanel {...baseProps} generationCount={2} attributesStale={false} />);
    expect(screen.getByText(/Attributes generated/)).toBeInTheDocument();
  });

  it('callsOnPreviewWhenPreviewButtonClicked', () => {
    const onPreview = vi.fn();
    render(<GeneratePanel {...baseProps} onPreview={onPreview} />);
    fireEvent.click(screen.getByText(/Preview/));
    expect(onPreview).toHaveBeenCalled();
  });

  it('callsOnGenerateWhenGenerateButtonClicked', () => {
    const onGenerate = vi.fn();
    render(<GeneratePanel {...baseProps} onGenerate={onGenerate} />);
    fireEvent.click(screen.getByText('Generate ↓'));
    expect(onGenerate).toHaveBeenCalled();
  });
});
