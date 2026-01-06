/**
 * Job results display component for completed/failed/cancelled jobs.
 * Supports both topic research (Drive folder) and video analysis (clips/quotes).
 *
 * Phase 3 (Jan 2026): Full Research Assistant Pipeline
 * - Pass 1: Clips & Quotes (existing)
 * - Pass 2: Content Blueprints (structure analysis)
 * - Pass 3: Gap Analysis (missing perspectives)
 * - Pass 4: Research Starter (actionable queries)
 */
import { useState } from 'react';
import { JobStatus } from './job-card-config';
import { ClipSheet, Clip } from './ClipSheet';
import { QuoteList, Quote } from './QuoteList';
import { ContentBlueprintView, ContentBlueprint } from './ContentBlueprintView';
import { GapAnalysisView, GapAnalysis } from './GapAnalysisView';
import { ResearchStarterView, ResearchStarter } from './ResearchStarterView';

interface VideoArtifacts {
  clips?: Clip[];
  quotes?: Quote[];
  producer_packet?: {
    title?: string;
    quality_gate?: {
      passes: boolean;
      failures: string[];
      clip_count: number;
      quote_count: number;
      verified_claim_count: number;
    };
    extraction_cost?: number;
  };
  quality_gate_passed?: boolean;
  // Phase 3: Full Research Assistant Pipeline
  content_blueprints?: ContentBlueprint[];
  gap_analysis?: GapAnalysis;
  research_starter?: ResearchStarter;
}

interface JobResultsProps {
  status: JobStatus;
  driveFolderUrl?: string;
  error?: string;
  pipeline?: string;
  artifacts?: VideoArtifacts;
}

type ResultTab = 'clips' | 'quotes' | 'blueprints' | 'gaps' | 'research';

export function JobResults({ status, driveFolderUrl, error, pipeline, artifacts }: JobResultsProps) {
  const [activeTab, setActiveTab] = useState<ResultTab>('clips');

  if (status === 'failed' && error) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-900/30 p-4">
        <h4 className="text-sm font-medium text-red-400 mb-1">Error</h4>
        <p className="text-sm text-red-300 break-words" style={{ overflowWrap: 'anywhere' }}>{error}</p>
      </div>
    );
  }

  if (status === 'cancelled') {
    return (
      <div className="rounded-lg border border-orange-800 bg-orange-900/30 p-4">
        <p className="text-sm text-orange-300">
          This job was cancelled. Any partial results may have been saved.
        </p>
      </div>
    );
  }

  // Video Analysis results
  if (status === 'completed' && pipeline === 'video_analysis' && artifacts) {
    const clips = artifacts.clips || [];
    const quotes = artifacts.quotes || [];
    const blueprints = artifacts.content_blueprints || [];
    const hasGapAnalysis = artifacts.gap_analysis && (
      (artifacts.gap_analysis.missing_perspectives?.length > 0) ||
      (artifacts.gap_analysis.unanswered_questions?.length > 0) ||
      (artifacts.gap_analysis.mentioned_but_unexplored?.length > 0) ||
      (artifacts.gap_analysis.contradictions?.length > 0)
    );
    const hasResearchStarter = artifacts.research_starter && (
      (artifacts.research_starter.search_queries?.length > 0) ||
      (artifacts.research_starter.source_suggestions?.length > 0) ||
      (artifacts.research_starter.content_angles?.length > 0)
    );
    const qualityGate = artifacts.producer_packet?.quality_gate;
    const passed = artifacts.quality_gate_passed ?? qualityGate?.passes ?? false;

    return (
      <div className="space-y-4">
        {/* Quality Gate Status */}
        <div className={`rounded-lg border p-4 ${
          passed
            ? 'border-green-800 bg-green-900/30'
            : 'border-yellow-800 bg-yellow-900/30'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${passed ? 'bg-green-800/50' : 'bg-yellow-800/50'}`}>
                {passed ? (
                  <svg className="h-6 w-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ) : (
                  <svg className="h-6 w-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                )}
              </div>
              <div>
                <p className={`font-medium ${passed ? 'text-green-300' : 'text-yellow-300'}`}>
                  {passed ? 'Video Analysis Complete' : 'Analysis Complete (Low Extraction)'}
                </p>
                <p className={`text-sm ${passed ? 'text-green-400/70' : 'text-yellow-400/70'}`}>
                  {clips.length} clips, {quotes.length} quotes extracted
                </p>
              </div>
            </div>

            {qualityGate && (
              <div className="text-xs text-gray-400 text-right">
                <div>Clips: {qualityGate.clip_count}/4</div>
                <div>Quotes: {qualityGate.quote_count}/8</div>
              </div>
            )}
          </div>

          {/* Quality gate failures */}
          {!passed && qualityGate?.failures && qualityGate.failures.length > 0 && (
            <div className="mt-3 pt-3 border-t border-yellow-800/50">
              <p className="text-xs text-yellow-400/70 mb-1">Quality thresholds not met:</p>
              <ul className="text-xs text-yellow-300/60 space-y-0.5">
                {qualityGate.failures.map((failure, idx) => (
                  <li key={idx}>- {failure}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Tabs for all outputs */}
        {(clips.length > 0 || quotes.length > 0 || blueprints.length > 0 || hasGapAnalysis || hasResearchStarter) && (
          <div>
            <div className="flex flex-wrap border-b border-gray-700 mb-4">
              <button
                onClick={() => setActiveTab('clips')}
                className={`px-3 py-2 text-sm font-medium transition ${
                  activeTab === 'clips'
                    ? 'text-purple-400 border-b-2 border-purple-400'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                Clips ({clips.length})
              </button>
              <button
                onClick={() => setActiveTab('quotes')}
                className={`px-3 py-2 text-sm font-medium transition ${
                  activeTab === 'quotes'
                    ? 'text-purple-400 border-b-2 border-purple-400'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                Quotes ({quotes.length})
              </button>
              {blueprints.length > 0 && (
                <button
                  onClick={() => setActiveTab('blueprints')}
                  className={`px-3 py-2 text-sm font-medium transition ${
                    activeTab === 'blueprints'
                      ? 'text-purple-400 border-b-2 border-purple-400'
                      : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  Blueprints ({blueprints.length})
                </button>
              )}
              {hasGapAnalysis && (
                <button
                  onClick={() => setActiveTab('gaps')}
                  className={`px-3 py-2 text-sm font-medium transition ${
                    activeTab === 'gaps'
                      ? 'text-purple-400 border-b-2 border-purple-400'
                      : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  Gaps
                </button>
              )}
              {hasResearchStarter && (
                <button
                  onClick={() => setActiveTab('research')}
                  className={`px-3 py-2 text-sm font-medium transition ${
                    activeTab === 'research'
                      ? 'text-purple-400 border-b-2 border-purple-400'
                      : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  Research
                </button>
              )}
            </div>

            <div className="max-h-[500px] overflow-y-auto">
              {activeTab === 'clips' && <ClipSheet clips={clips} />}
              {activeTab === 'quotes' && <QuoteList quotes={quotes} />}
              {activeTab === 'blueprints' && blueprints.length > 0 && (
                <ContentBlueprintView blueprints={blueprints} />
              )}
              {activeTab === 'gaps' && hasGapAnalysis && (
                <GapAnalysisView gapAnalysis={artifacts.gap_analysis!} />
              )}
              {activeTab === 'research' && hasResearchStarter && (
                <ResearchStarterView researchStarter={artifacts.research_starter!} />
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Topic Research results (Drive folder)
  if (status === 'completed' && driveFolderUrl) {
    return (
      <div className="rounded-lg border border-green-800 bg-green-900/30 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-800/50 rounded-lg">
              <svg
                className="h-6 w-6 text-green-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                />
              </svg>
            </div>
            <div>
              <p className="font-medium text-green-300">Research Complete</p>
              <p className="text-sm text-green-400/70">
                Your documents are ready
              </p>
            </div>
          </div>
          <a
            href={driveFolderUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-500"
            onClick={(e) => e.stopPropagation()}
          >
            Open in Drive
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        </div>
      </div>
    );
  }

  return null;
}

export default JobResults;
