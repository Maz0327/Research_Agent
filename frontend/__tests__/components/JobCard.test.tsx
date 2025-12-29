/**
 * Tests for the JobCard component.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import JobCard from '../../components/JobCard';
import { Job } from '../../store/jobs';

// Mock framer-motion with React.createElement to avoid JSX parsing issues
jest.mock('framer-motion', () => ({
  motion: {
    div: React.forwardRef(function MotionDiv(
      { children, layout, initial, animate, exit, transition, ...props }: React.PropsWithChildren<Record<string, unknown>>,
      ref: React.Ref<HTMLDivElement>
    ) {
      // Filter out framer-motion specific props
      void layout; void initial; void animate; void exit; void transition;
      return React.createElement('div', { ...props, ref }, children);
    }),
    svg: React.forwardRef(function MotionSvg(
      { children, animate, transition, ...props }: React.PropsWithChildren<Record<string, unknown>>,
      ref: React.Ref<SVGSVGElement>
    ) {
      // Filter out framer-motion specific props
      void animate; void transition;
      return React.createElement('svg', { ...props, ref }, children);
    }),
  },
  AnimatePresence: ({ children }: React.PropsWithChildren<object>) => children,
}));

// Mock useETA hook
jest.mock('../../hooks/useETA', () => ({
  __esModule: true,
  default: () => ({
    eta: '5 min',
    elapsed: '2 min',
    stageDescription: 'Processing sources',
  }),
}));

// Mock job-card sub-components using React.createElement
jest.mock('../../components/job-card', () => ({
  statusConfig: {
    queued: { borderColor: 'border-gray-600' },
    running: { borderColor: 'border-blue-600' },
    completed: { borderColor: 'border-green-600' },
    failed: { borderColor: 'border-red-600' },
    cancelled: { borderColor: 'border-yellow-600' },
  },
  pipelineLabels: {
    quick: 'Quick',
    full: 'Full',
    investigation: 'Investigation',
    breaking_news: 'Breaking News',
  },
  StatusBadge: ({ status }: { status: string }) =>
    React.createElement('span', { 'data-testid': 'status-badge' }, status),
  ProgressBar: ({ progress }: { progress: number }) =>
    React.createElement('div', { 'data-testid': 'progress-bar', 'data-progress': progress }),
  JobResults: ({
    status,
    driveFolderUrl,
    error,
  }: {
    status: string;
    driveFolderUrl?: string;
    error?: string;
  }) =>
    React.createElement(
      'div',
      { 'data-testid': 'job-results' },
      status === 'completed' && driveFolderUrl
        ? React.createElement('a', { href: driveFolderUrl }, 'View Results')
        : null,
      error ? React.createElement('span', null, 'Error: ' + error) : null
    ),
  JobActions: ({
    jobId,
    onRefresh,
  }: {
    jobId: string;
    status: string;
    driveFolderUrl?: string;
    onRefresh?: () => void;
  }) =>
    React.createElement(
      'div',
      { 'data-testid': 'job-actions' },
      React.createElement(
        'button',
        { onClick: onRefresh, 'data-testid': `refresh-${jobId}` },
        'Refresh'
      )
    ),
}));

describe('JobCard', () => {
  const mockJob: Job = {
    id: 'job-123',
    prompt: 'Research topic about AI',
    title: 'AI Research',
    pipeline: 'investigation',
    status: 'running',
    progress_percent: 50,
    created_at: '2025-01-01T12:00:00Z',
  };

  it('should render job title', () => {
    render(<JobCard job={mockJob} />);
    expect(screen.getByText('AI Research')).toBeInTheDocument();
  });

  it('should render pipeline label', () => {
    render(<JobCard job={mockJob} />);
    expect(screen.getByText('Investigation')).toBeInTheDocument();
  });

  it('should render status badge', () => {
    render(<JobCard job={mockJob} />);
    expect(screen.getByTestId('status-badge')).toHaveTextContent('running');
  });

  it('should render progress bar for running job', () => {
    render(<JobCard job={mockJob} />);
    const progressBar = screen.getByTestId('progress-bar');
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute('data-progress', '50');
  });

  it('should render ETA for running job', () => {
    render(<JobCard job={mockJob} />);
    expect(screen.getByText('ETA: 5 min')).toBeInTheDocument();
  });

  it('should expand on click', () => {
    render(<JobCard job={mockJob} />);

    // Find the button and click it
    const expandButton = screen.getByRole('button', { name: /Job: AI Research/i });
    fireEvent.click(expandButton);

    // After expansion, should show job actions
    expect(screen.getByTestId('job-actions')).toBeInTheDocument();
  });

  it('should expand on Enter key', () => {
    render(<JobCard job={mockJob} />);

    const expandButton = screen.getByRole('button', { name: /Job: AI Research/i });
    fireEvent.keyDown(expandButton, { key: 'Enter' });

    expect(screen.getByTestId('job-actions')).toBeInTheDocument();
  });

  it('should expand on Space key', () => {
    render(<JobCard job={mockJob} />);

    const expandButton = screen.getByRole('button', { name: /Job: AI Research/i });
    fireEvent.keyDown(expandButton, { key: ' ' });

    expect(screen.getByTestId('job-actions')).toBeInTheDocument();
  });

  it('should have correct aria-expanded attribute', () => {
    render(<JobCard job={mockJob} />);

    const expandButton = screen.getByRole('button', { name: /Job: AI Research/i });
    expect(expandButton).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(expandButton);
    expect(expandButton).toHaveAttribute('aria-expanded', 'true');
  });

  it('should call onRefresh when refresh button clicked', () => {
    const onRefresh = jest.fn();
    render(<JobCard job={mockJob} onRefresh={onRefresh} />);

    // Expand first
    fireEvent.click(screen.getByRole('button', { name: /Job: AI Research/i }));

    // Click refresh
    fireEvent.click(screen.getByTestId('refresh-job-123'));
    expect(onRefresh).toHaveBeenCalled();
  });

  it('should truncate long prompts without title', () => {
    const longPromptJob: Job = {
      ...mockJob,
      title: undefined,
      prompt:
        'This is a very long prompt that should be truncated because it exceeds fifty characters',
    };

    render(<JobCard job={longPromptJob} />);
    expect(
      screen.getByText(/This is a very long prompt that should be truncate\.\.\./)
    ).toBeInTheDocument();
  });

  it('should not render progress bar for completed job', () => {
    const completedJob: Job = {
      ...mockJob,
      status: 'completed',
      progress_percent: 100,
    };

    render(<JobCard job={completedJob} />);
    expect(screen.queryByTestId('progress-bar')).not.toBeInTheDocument();
  });

  it('should show error for failed job', () => {
    const failedJob: Job = {
      ...mockJob,
      status: 'failed',
      error: 'Something went wrong',
    };

    render(<JobCard job={failedJob} />);

    // Expand to see error
    fireEvent.click(screen.getByRole('button', { name: /Job: AI Research/i }));
    expect(screen.getByText('Error: Something went wrong')).toBeInTheDocument();
  });
});
