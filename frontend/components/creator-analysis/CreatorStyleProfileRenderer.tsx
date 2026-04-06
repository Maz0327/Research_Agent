/**
 * CreatorStyleProfileRenderer — Renders a Creator Style Profile document.
 *
 * Shows hook patterns, narrative structure, vocabulary fingerprint,
 * aesthetic keywords, and tone descriptors. Includes a "Save as Style Guide"
 * button that creates a new personal style guide from the profile.
 */

import { useState, useCallback } from 'react';
import { CardWrapper } from '../document/shared/CardWrapper';
import { CollapsibleSection } from '../document/shared/CollapsibleSection';
import { useStyleGuideStore } from '../../store/style-guides';

interface CreatorStyleProfile {
  creator_name: string;
  channel_description: string;
  content_niche: string;
  hook_patterns: Array<{
    hook_type: string;
    example: string;
    frequency: string;
  }>;
  narrative_structure: {
    primary_structure: string;
    structure_description: string;
    pacing: string;
    transition_style: string;
  };
  vocabulary_fingerprint: {
    signature_phrases: string[];
    filler_words: string[];
    unique_expressions: string[];
    tone_markers: string[];
  };
  aesthetic_profile: {
    visual_style: string;
    color_palette: string;
    broll_style: string;
    music_tone: string;
    pacing_descriptors: string[];
    typography_style: string;
  };
  tone_descriptors: {
    formality: string;
    humor_usage: string;
    emotional_range: string;
    authority_level: string;
    energy_level: string;
  };
  style_summary: string;
  recommended_voice: string;
  recommended_hook_style: string;
  recommended_structure: string;
}

interface CreatorStyleProfileRendererProps {
  profile: CreatorStyleProfile;
  videoCount: number;
  onBack: () => void;
}

const FREQUENCY_COLORS: Record<string, string> = {
  very_common: 'text-green-400 bg-green-900/30 border-green-700/50',
  common: 'text-blue-400 bg-blue-900/30 border-blue-700/50',
  occasional: 'text-muted-foreground bg-card/50 border-border/50',
};

const HOOK_TYPE_COLORS: Record<string, string> = {
  question: 'text-blue-400',
  stat: 'text-green-400',
  story: 'text-purple-400',
  contradiction: 'text-red-400',
  visual: 'text-amber-400',
};

function formatLabel(s: string): string {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function CreatorStyleProfileRenderer({
  profile,
  videoCount,
  onBack,
}: CreatorStyleProfileRendererProps) {
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const { createGuide } = useStyleGuideStore();

  const handleSaveAsStyleGuide = useCallback(async () => {
    setSaveStatus('saving');
    try {
      const guide = await createGuide({
        name: `${profile.creator_name} Style`,
        template_base: 'custom',
        overrides: {
          voice: profile.recommended_voice,
          hook_style: profile.recommended_hook_style,
          structure: profile.recommended_structure,
          vocabulary_use: profile.vocabulary_fingerprint.signature_phrases.slice(0, 6),
          vocabulary_avoid: profile.vocabulary_fingerprint.filler_words.slice(0, 6),
          inspirations: [profile.creator_name],
        },
      });
      setSaveStatus(guide ? 'saved' : 'error');
    } catch {
      setSaveStatus('error');
    }
  }, [createGuide, profile]);

  return (
    <div className="space-y-6">
      {/* Back + header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-3"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          <h2 className="text-xl font-bold text-foreground">
            {profile.creator_name} — Style Profile
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Analyzed from {videoCount} video{videoCount !== 1 ? 's' : ''} &middot; {profile.content_niche}
          </p>
        </div>

        {/* Save as Style Guide button */}
        <button
          onClick={handleSaveAsStyleGuide}
          disabled={saveStatus === 'saving' || saveStatus === 'saved'}
          className={`
            flex-shrink-0 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
            ${saveStatus === 'saved'
              ? 'bg-green-900/40 text-green-400 border border-green-700/40'
              : saveStatus === 'error'
                ? 'bg-red-900/40 text-red-400 border border-red-700/40 hover:bg-red-900/60'
                : 'bg-purple-600/20 text-purple-300 border border-purple-700/40 hover:bg-purple-600/30'
            }
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        >
          {saveStatus === 'saving' ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Saving...
            </>
          ) : saveStatus === 'saved' ? (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Saved as Style Guide
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
              </svg>
              Save as Style Guide
            </>
          )}
        </button>
      </div>

      {/* Style Summary */}
      <CardWrapper accentColor="bg-purple-500">
        <p className="text-caption font-medium text-purple-400 uppercase tracking-wider mb-2">Style Summary</p>
        <p className="text-body-lg text-foreground leading-relaxed">{profile.style_summary}</p>
        <p className="text-body-sm text-muted-foreground mt-3 italic">{profile.channel_description}</p>
      </CardWrapper>

      {/* Hook Patterns */}
      <div>
        <p className="text-body-sm font-semibold text-muted-foreground/70 uppercase tracking-wider mb-3">
          Hook Patterns ({profile.hook_patterns.length})
        </p>
        <div className="space-y-2">
          {profile.hook_patterns.map((hook, i) => (
            <div
              key={i}
              className="rounded-lg border border-border/50 bg-card/40 p-3"
            >
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`text-body-sm font-semibold ${HOOK_TYPE_COLORS[hook.hook_type] || 'text-muted-foreground'}`}>
                  {formatLabel(hook.hook_type)}
                </span>
                <span className={`text-caption px-1.5 py-0.5 rounded border ${FREQUENCY_COLORS[hook.frequency] || FREQUENCY_COLORS.occasional}`}>
                  {formatLabel(hook.frequency)}
                </span>
              </div>
              <p className="text-body-sm text-muted-foreground italic">&ldquo;{hook.example}&rdquo;</p>
            </div>
          ))}
        </div>
      </div>

      {/* Narrative Structure */}
      <CardWrapper accentColor="bg-blue-500">
        <p className="text-caption font-medium text-blue-400 uppercase tracking-wider mb-2">Narrative Structure</p>
        <div className="space-y-2">
          <div>
            <p className="text-body-sm text-muted-foreground/70 font-medium">Primary Structure</p>
            <p className="text-body text-foreground">{formatLabel(profile.narrative_structure.primary_structure)}</p>
          </div>
          <p className="text-body-sm text-muted-foreground">{profile.narrative_structure.structure_description}</p>
          <div className="flex gap-4 pt-1">
            <div>
              <p className="text-caption text-muted-foreground/70">Pacing</p>
              <p className="text-body-sm text-muted-foreground">{formatLabel(profile.narrative_structure.pacing)}</p>
            </div>
            <div>
              <p className="text-caption text-muted-foreground/70">Transitions</p>
              <p className="text-body-sm text-muted-foreground">{profile.narrative_structure.transition_style}</p>
            </div>
          </div>
        </div>
      </CardWrapper>

      {/* Vocabulary Fingerprint */}
      <div>
        <p className="text-body-sm font-semibold text-muted-foreground/70 uppercase tracking-wider mb-3">Vocabulary Fingerprint</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="rounded-lg border border-border/50 bg-card/40 p-3">
            <p className="text-caption text-green-400 font-medium mb-2">Signature Phrases</p>
            <div className="flex flex-wrap gap-1.5">
              {profile.vocabulary_fingerprint.signature_phrases.map((p, i) => (
                <span key={i} className="text-caption px-2 py-0.5 rounded-full bg-green-900/30 text-green-300 border border-green-700/40">
                  {p}
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-lg border border-border/50 bg-card/40 p-3">
            <p className="text-caption text-amber-400 font-medium mb-2">Unique Expressions</p>
            <div className="flex flex-wrap gap-1.5">
              {profile.vocabulary_fingerprint.unique_expressions.map((p, i) => (
                <span key={i} className="text-caption px-2 py-0.5 rounded-full bg-amber-900/30 text-amber-300 border border-amber-700/40">
                  {p}
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-lg border border-border/50 bg-card/40 p-3">
            <p className="text-caption text-blue-400 font-medium mb-2">Tone Markers</p>
            <div className="flex flex-wrap gap-1.5">
              {profile.vocabulary_fingerprint.tone_markers.map((p, i) => (
                <span key={i} className="text-caption px-2 py-0.5 rounded-full bg-blue-900/30 text-blue-300 border border-blue-700/40">
                  {p}
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-lg border border-border/50 bg-card/40 p-3">
            <p className="text-caption text-red-400 font-medium mb-2">Filler Words to Note</p>
            <div className="flex flex-wrap gap-1.5">
              {profile.vocabulary_fingerprint.filler_words.map((p, i) => (
                <span key={i} className="text-caption px-2 py-0.5 rounded-full bg-red-900/30 text-red-300 border border-red-700/40">
                  {p}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Tone Descriptors */}
      <CollapsibleSection label="Tone Descriptors" defaultOpen>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {Object.entries(profile.tone_descriptors).map(([key, value]) => (
            <div key={key} className="text-center p-3 rounded-lg border border-border/50 bg-card/40">
              <p className="text-caption text-muted-foreground/70 uppercase tracking-wider mb-1">{formatLabel(key)}</p>
              <p className="text-body-sm text-foreground font-medium">{formatLabel(value)}</p>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      {/* Aesthetic Profile */}
      <CollapsibleSection label="Aesthetic Profile">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { label: 'Visual Style', value: profile.aesthetic_profile.visual_style },
            { label: 'Color Palette', value: profile.aesthetic_profile.color_palette },
            { label: 'B-Roll Style', value: profile.aesthetic_profile.broll_style },
            { label: 'Music Tone', value: profile.aesthetic_profile.music_tone },
            { label: 'Typography', value: profile.aesthetic_profile.typography_style },
          ].map((item) => (
            <div key={item.label} className="rounded-lg border border-border/50 bg-card/40 p-3">
              <p className="text-caption text-muted-foreground/70 font-medium mb-1">{item.label}</p>
              <p className="text-body-sm text-muted-foreground">{item.value}</p>
            </div>
          ))}
          <div className="rounded-lg border border-border/50 bg-card/40 p-3">
            <p className="text-caption text-muted-foreground/70 font-medium mb-1">Pacing</p>
            <div className="flex flex-wrap gap-1">
              {profile.aesthetic_profile.pacing_descriptors.map((d, i) => (
                <span key={i} className="text-caption px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground">
                  {d}
                </span>
              ))}
            </div>
          </div>
        </div>
      </CollapsibleSection>

      {/* Recommendations */}
      <CardWrapper accentColor="bg-amber-500">
        <p className="text-caption font-medium text-amber-400 uppercase tracking-wider mb-3">Recommendations</p>
        <div className="space-y-3">
          <div>
            <p className="text-body-sm text-muted-foreground/70 font-medium">Voice</p>
            <p className="text-body-sm text-muted-foreground">{profile.recommended_voice}</p>
          </div>
          <div>
            <p className="text-body-sm text-muted-foreground/70 font-medium">Hook Style</p>
            <p className="text-body-sm text-muted-foreground">{profile.recommended_hook_style}</p>
          </div>
          <div>
            <p className="text-body-sm text-muted-foreground/70 font-medium">Structure</p>
            <p className="text-body-sm text-muted-foreground">{profile.recommended_structure}</p>
          </div>
        </div>
      </CardWrapper>
    </div>
  );
}
