/**
 * TypeScript interfaces for Research Agent document JSON data.
 *
 * These match the Python backend `to_dict()` output shapes exactly.
 * Used by the typed document renderers to consume JSON directly
 * instead of parsing markdown.
 */

// =============================================================================
// Enums
// =============================================================================

export type ConfidenceLevel = 'high' | 'medium' | 'low';
export type AnalysisMode = 'transcript_grounded' | 'caption_grounded' | 'video_only' | 'text_provided' | 'ocr_extracted' | 'article_fetched';
export type SourceStatus = 'ingested' | 'partial' | 'failed';
export type TriageLevel = 'ready' | 'usable' | 'thin' | 'degraded' | 'failed';

// =============================================================================
// Core Semantic Units
// =============================================================================

export interface KeyPoint {
  key_point_id: string;
  statement: string;
  source_ids: string[];
  confidence: ConfidenceLevel;
  supporting_claims: string[];
}

export interface Theme {
  theme_id: string;
  label: string;
  description: string;
  related_key_points: string[];
  sources_supporting: string[];
  is_consensus: boolean;
  confidence?: ConfidenceLevel;
}

export interface Gap {
  gap_id: string;
  label: string;
  description: string;
  why_expected: string;
  related_themes: string[];
  related_key_points: string[];
  suggested_research_direction?: string;
}

export interface Tension {
  tension_id: string;
  label: string;
  description: string;
  involved_key_points: string[];
  source_ids: string[];
  sources_position_a: string[];
  sources_position_b: string[];
  is_cross_source: boolean;
  confidence?: ConfidenceLevel;
}

export interface SpeculativeObservation {
  text: string;
  based_on: string[];
  label: 'speculative';
}

// =============================================================================
// Source Ledger (Doc 0)
// =============================================================================

export interface TranscriptProvenance {
  transcript_source: string;
  transcript_status: string;
  captions_status: string;
  gemini_analysis_mode: AnalysisMode;
  notes?: string | null;
}

export interface ExtractedIndex {
  claim_ids: string[];
  entity_names: string[];
  theme_ids: string[];
}

export interface SourceEntry {
  source_id: string;
  source_type: string;
  title: string;
  url: string;
  status: SourceStatus;
  creator?: string | null;
  published?: string | null;
  duration?: string | null;
  word_count?: number | null;
  skim_summary: string[];
  extracted_index: ExtractedIndex;
  full_text?: string | null;
  full_text_unavailable_reason?: string | null;
  transcript_provenance?: TranscriptProvenance | null;
  failure_reason?: string | null;
}

export interface SourceLedgerData {
  document_type: 'source_ledger';
  topic: string;
  source_manifest: { source_id: string; type: string; title: string; status: SourceStatus }[];
  sources: SourceEntry[];
  created_at: string;
}

// =============================================================================
// Jump-Start Directions (Doc 1)
// =============================================================================

export interface ResearchDirection {
  priority: number;
  what_to_look_for: string;
  example_queries: string[];
  why_it_matters: string;
}

export interface BoosterItem {
  query?: string;
  question?: string;
  description?: string;
  impact_level?: 'critical' | 'important' | 'nice_to_have';
  why_it_matters?: string;
  search_suggestion?: string;
  purpose?: string;
  platform_suggestion?: string;
}

export interface ResearchThread {
  theme: Theme;
  key_points: KeyPoint[];
  gaps: Gap[];
  research_directions: ResearchDirection[];
  booster_search_queries: BoosterItem[];
  booster_research_questions: BoosterItem[];
  booster_primary_sources: BoosterItem[];
  booster_missing_perspectives: BoosterItem[];
}

export interface CrossCuttingAnalysis {
  confirmed: { statement: string; sources: string[] }[];
  conflicts: { description: string; sources_a: string[]; sources_b: string[] }[];
  single_source: { statement: string; source: string }[];
}

export interface JumpStartData {
  document_type: 'jump_start';
  scope_lock: { in: string[]; out: string[] };
  current_corpus: {
    source_count: number;
    perspectives_represented: string[];
    time_span_covered?: string | null;
  };
  key_points: KeyPoint[];
  tensions: Tension[];
  gaps: Gap[];
  research_directions: ResearchDirection[];
  next_steps: string[];
  confidence: ConfidenceLevel;
  warnings: string[];
  created_at: string;
  research_threads: ResearchThread[];
  cross_cutting?: CrossCuttingAnalysis | null;
}

// =============================================================================
// Semantic Brief (Doc 2)
// =============================================================================

export interface ConfidenceAssessment {
  level: ConfidenceLevel;
  reasoning: string[];
}

export interface SCQA {
  situation: string;
  complication: string;
  question?: string;
  answer?: string;
}

export interface SemanticBriefData {
  document_type: 'semantic_brief';
  semantic_core: { text: string; based_on: string[] };
  themes: Theme[];
  key_points: KeyPoint[];
  tensions: Tension[];
  gaps: Gap[];
  confidence_assessment: ConfidenceAssessment;
  speculative_observations: SpeculativeObservation[];
  triage: TriageLevel;
  warnings: string[];
  created_at: string;
  scqa?: SCQA | null;
  source_ids: string[];
  source_coverage?: Record<string, string[]> | null;
}

// =============================================================================
// Creator Brief / Producer Packet (Doc 3)
// =============================================================================

export interface StoryCore {
  central_question: string;
  one_sentence_pitch: string;
  why_this_matters: string;
  target_audience: string;
  emotional_arc: string;
}

export interface NarrativeAngle {
  angle_id: string;
  title: string;
  description: string;
  strengths: string[];
  weaknesses: string[];
  best_for: string;
  key_sources: string[];
  confidence: string;
}

export interface OpeningHook {
  hook_type: string;
  content: string;
  tone: string;
  source_basis: string[];
}

export interface KeyMoment {
  moment: string;
  source_id: string;
  timestamp?: string | null;
  why_compelling: string;
  potential_use: string;
}

export interface TitleOption {
  title: string;
  subtitle?: string | null;
  tone: string;
}

export interface ThumbnailConcept {
  concept: string;
  visual_elements: string[];
  text_overlay?: string | null;
  emotional_appeal: string;
}

export interface StructureOption {
  structure_type: string;
  description: string;
  section_breakdown: string[];
  pros: string[];
  cons: string[];
}

export interface RiskAssessment {
  sensitivity_level: string;
  potential_issues: string[];
  mitigation_suggestions: string[];
  legal_considerations: string[];
  ethical_considerations: string[];
}

export interface BRollSuggestion {
  description: string;
  source_id?: string | null;
  timestamp?: string | null;
  visual_type?: string;
}

export interface InterviewSuggestions {
  suggested_guests: { name: string; why: string; source_id?: string }[];
  key_questions: string[];
}

export interface StoryBeat {
  beat_number: number;
  label: string;
  description: string;
  mapped_ids?: string[];
}

export interface StoryArc {
  arc_name: string;
  arc_type: 'cold_open' | 'multiple_perspectives' | 'heros_journey' | 'discovery';
  beats: StoryBeat[];
  scripting_preview: string;
  topic_fit_reason: string;
}

export interface ProductionBlueprint {
  estimated_runtime?: string | null;
  pacing_notes?: string[];
  equipment_notes?: string[];
  [key: string]: unknown;
}

export interface StoryLandscape {
  primary_conflict?: string;
  stakes?: string;
  characters?: { name: string; role: string; source_id?: string }[];
  timeline?: string;
  [key: string]: unknown;
}

export interface ProducerPacketData {
  document_type: 'producer_packet';
  document_version?: string;
  job_id?: string;
  generated_at?: string;
  creative_interpretation_notice?: string;
  story_core: StoryCore;
  story_landscape?: StoryLandscape | null;
  narrative_angles: NarrativeAngle[];
  opening_hooks: OpeningHook[];
  structure_options: StructureOption[];
  key_moments: KeyMoment[];
  title_options: TitleOption[];
  thumbnail_concepts: ThumbnailConcept[];
  risk_assessment?: RiskAssessment | null;
  interview_suggestions?: InterviewSuggestions | null;
  b_roll_suggestions?: BRollSuggestion[];
  production_blueprint?: ProductionBlueprint | null;
  recommended_angle_id?: string | null;
  recommendation_reasoning: string;
  risk_if_wrong?: string | null;
  pivot_angle_id?: string | null;
  pivot_reasoning?: string | null;
  decision_criteria?: string[] | null;
  quality_score?: number | null;
  quality_issues?: string[];
  suggested_structure?: StoryArc;
  [key: string]: unknown;
}

// =============================================================================
// Blog Post (Doc 7)
// =============================================================================

export interface BlogSection {
  section_id: string;
  heading: string;
  body: string;
  claim_ids: string[];
  source_ids: string[];
}

export interface BlogPostData {
  document_type: 'blog_post';
  job_id: string;
  generated_at: string;
  topic: string;
  source_count: number;
  title: string;
  subtitle?: string | null;
  meta_description: string;
  estimated_reading_time: string;
  sections: BlogSection[];
  conclusion: string;
  call_to_action?: string | null;
  seo_keywords: string[];
  description_sources: { source_id: string; title: string; url?: string; creator?: string }[];
  guardrails: {
    no_new_facts_ack: boolean;
    all_facts_reference_doc2: boolean;
    all_facts_reference_doc0: boolean;
  };
}

// =============================================================================
// Script (Doc 5)
// =============================================================================

export interface ScriptHook {
  text: string;
  hook_type: string;
  claim_id: string;
  source_id: string;
}

export interface ScriptSection {
  section_id: string;
  beat_label: string;
  spoken_text: string;
  stage_direction?: string | null;
  duration_estimate: string;
  claim_ids: string[];
  source_ids: string[];
}

export interface ScriptOutro {
  text: string;
  call_to_action?: string | null;
}

export interface ScriptData {
  document_type: 'script';
  job_id: string;
  generated_at: string;
  topic: string;
  source_count: number;
  tone: 'serious' | 'casual' | 'energetic' | 'conversational';
  target_length: 'short' | 'medium' | 'long';
  story_arc: string;
  title: string;
  hook: ScriptHook;
  sections: ScriptSection[];
  outro: ScriptOutro;
  total_word_count: number;
  estimated_duration: string;
  description_sources: { source_id: string; title: string; url?: string; creator?: string }[];
  guardrails: {
    no_new_facts_ack: boolean;
    all_facts_reference_doc2: boolean;
    all_facts_reference_doc0: boolean;
  };
}

// =============================================================================
// Social Media Kit (Doc 6)
// =============================================================================

export interface TweetItem {
  tweet_number: number;
  text: string;
  claim_ids: string[];
}

export interface TimestampEntry {
  timestamp: string;
  label: string;
}

export type SocialPlatform = 'twitter_thread' | 'linkedin' | 'instagram' | 'youtube_description' | 'tiktok' | 'newsletter';

export interface PlatformPost {
  platform: SocialPlatform;
  tweets?: TweetItem[];
  body?: string | null;
  description_body?: string | null;
  timestamps?: TimestampEntry[];
  hashtags: string[];
  char_count: number;
  claim_ids: string[];
  source_ids: string[];
}

export interface SocialKitData {
  document_type: 'social_kit';
  job_id: string;
  generated_at: string;
  topic: string;
  source_count: number;
  platforms: PlatformPost[];
  guardrails: {
    no_new_facts_ack: boolean;
    all_facts_reference_doc2: boolean;
    all_facts_reference_doc0: boolean;
  };
}

// =============================================================================
// Union type for all document data
// =============================================================================

export type DocumentData = SourceLedgerData | JumpStartData | SemanticBriefData | ProducerPacketData | BlogPostData | ScriptData | SocialKitData;
