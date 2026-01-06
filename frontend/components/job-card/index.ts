/**
 * Job card components barrel export.
 */
export { statusConfig, pipelineLabels } from './job-card-config';
export type { JobStatus, StatusConfig } from './job-card-config';

export { ClipSheet } from './ClipSheet';
export type { Clip } from './ClipSheet';
export { DisambiguationPanel } from './DisambiguationPanel';
export { JobActions } from './JobActions';
export { JobResults } from './JobResults';
export { ProgressBar } from './ProgressBar';
export { QuoteList } from './QuoteList';
export type { Quote } from './QuoteList';
export { StatusBadge } from './StatusBadge';

// Phase 3: Full Research Assistant Pipeline (Jan 2026)
export { ContentBlueprintView } from './ContentBlueprintView';
export type { ContentBlueprint, ActSection, OpenLoop } from './ContentBlueprintView';
export { GapAnalysisView } from './GapAnalysisView';
export type { GapAnalysis, MissingPerspective, CoverageBlindSpot, Contradiction } from './GapAnalysisView';
export { ResearchStarterView } from './ResearchStarterView';
export type { ResearchStarter, SearchQuery, SourceSuggestion, RabbitHole, ContentAngle } from './ResearchStarterView';
