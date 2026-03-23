'use client';

/**
 * SharedJobView — Public read-only document page.
 * Gradient header, metadata badges, document tabs, hook + key findings preview.
 * No sidebar/layout — standalone public page.
 */

import { useState } from 'react';
import Link from 'next/link';
import { Download, Link as LinkIcon } from 'lucide-react';
import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';
import { transformMarkdownWithDetails } from '@/lib/document-formatters';
import { formatExpiration, extractHook, extractKeyFindings } from './shared-view-helpers';

interface SharedDocument {
  job_id: string;
  job_title: string | null;
  doc_type: string;
  doc_title: string;
  markdown: string | null;
  data: Record<string, unknown> | null;
  expires_at: string;
  view_count: number;
}

interface SharedJobViewProps {
  document: SharedDocument;
}

const DOC_TABS = ['Creator Brief', 'Semantic Brief', 'Source Ledger'] as const;
type DocTab = typeof DOC_TABS[number];

export function SharedJobView({ document }: SharedJobViewProps) {
  const [activeTab, setActiveTab] = useState<DocTab>('Creator Brief');
  const [copied, setCopied] = useState(false);

  const hook = extractHook(document.markdown);
  const keyFindings = extractKeyFindings(document.markdown);
  const expiry = formatExpiration(document.expires_at);
  const hasPreview = hook || keyFindings.length > 0;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Minimal header */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center shrink-0">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span className="text-sm font-semibold text-foreground">Research Agent</span>
          <span className="text-border text-sm mx-1">—</span>
          <span className="text-sm text-muted-foreground">Shared Research</span>
        </div>
      </header>

      <main id="main-content" className="flex-1 max-w-3xl mx-auto w-full px-4 py-8">
        <div className="bg-card border border-border rounded-2xl overflow-hidden">

          {/* Gradient header */}
          <div className="bg-gradient-to-r from-accent-blue/10 to-accent-purple/10 px-6 py-5 border-b border-border">
            <div className="flex items-start gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center shrink-0">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="min-w-0">
                <h1 className="text-lg font-bold text-foreground leading-snug">
                  {document.job_title || document.doc_title}
                </h1>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Research Agent &middot;{' '}
                  {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs px-2 py-0.5 rounded bg-background/50 text-muted-foreground border border-border/50">
                {document.view_count} view{document.view_count !== 1 ? 's' : ''}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-background/50 text-muted-foreground border border-border/50">
                {document.doc_type.replace(/_/g, ' ')}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-background/50 text-muted-foreground border border-border/50">
                {expiry}
              </span>
            </div>
          </div>

          {/* Document tabs */}
          <div className="px-6 border-b border-border">
            <div className="flex gap-6">
              {DOC_TABS.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`py-3 text-sm border-b-2 transition-colors cursor-pointer ${
                    activeTab === tab
                      ? 'text-accent-blue font-medium border-accent-blue'
                      : 'text-muted-foreground border-transparent hover:text-foreground'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="px-6 py-5">
            {hook && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-amber-500 mb-2">Hook</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{hook}</p>
              </div>
            )}

            {keyFindings.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-foreground mb-2">Key Findings</h3>
                <div className="space-y-2">
                  {keyFindings.map((finding, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="w-4 h-4 rounded-full bg-accent-green/10 flex items-center justify-center shrink-0 mt-0.5 text-[8px] font-bold text-accent-green">
                        {i + 1}
                      </span>
                      <p className="text-xs text-muted-foreground">{finding}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Full content fallback when no structured preview available */}
            {!hasPreview && (
              <div className="overflow-auto max-h-[60vh]">
                {document.markdown ? (
                  <MarkdownRenderer content={transformMarkdownWithDetails(document.markdown, false)} />
                ) : document.data ? (
                  <pre className="text-sm text-muted-foreground font-mono whitespace-pre-wrap bg-muted/30 rounded-lg p-4 overflow-x-auto">
                    {JSON.stringify(document.data, null, 2)}
                  </pre>
                ) : (
                  <p className="text-muted-foreground text-center py-8">No content available</p>
                )}
              </div>
            )}

            {/* Footer actions */}
            <div className="flex items-center gap-4 pt-4 border-t border-border mt-2">
              <button className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
                <Download className="w-3.5 h-3.5" />
                Download PDF
              </button>
              <button
                onClick={handleCopyLink}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              >
                <LinkIcon className="w-3.5 h-3.5" />
                {copied ? 'Copied!' : 'Copy Link'}
              </button>
              <span className="text-[10px] text-muted-foreground ml-auto">{expiry}</span>
            </div>
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-muted-foreground">
          Shared from{' '}
          <Link href="/" className="text-accent-blue hover:text-accent-blue/80 transition">
            Research Agent
          </Link>
        </div>
      </main>
    </div>
  );
}
