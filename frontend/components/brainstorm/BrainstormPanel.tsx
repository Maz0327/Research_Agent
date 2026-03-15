/**
 * BrainstormPanel — Creative angle exploration before source discovery.
 *
 * Displays AI-generated narrative angles, vocabulary, key questions,
 * and search suggestions. User selects angles and vocabulary, then
 * proceeds to source discovery with enriched context.
 */

import { useState } from 'react';
import { AngleCard, type BrainstormAngleData } from './AngleCard';

interface BrainstormResult {
  angles: BrainstormAngleData[];
  vocabulary: string[];
  key_questions: string[];
  aesthetic_keywords: string[];
  suggested_search_queries: string[];
  cost: number;
}

interface BrainstormPanelProps {
  result: BrainstormResult;
  topic: string;
  onProceed: (selected: {
    angles: string[];
    vocabulary: string[];
    questions: string[];
  }) => void;
  onBack: () => void;
}

export function BrainstormPanel({ result, topic, onProceed, onBack }: BrainstormPanelProps) {
  const [selectedAngles, setSelectedAngles] = useState<Set<string>>(new Set());
  const [deselectedVocab, setDeselectedVocab] = useState<Set<string>>(new Set());
  const [selectedQuestions, setSelectedQuestions] = useState<Set<string>>(
    new Set(result.key_questions)
  );
  const [customQuestion, setCustomQuestion] = useState('');

  const toggleAngle = (angleId: string) => {
    setSelectedAngles(prev => {
      const next = new Set(prev);
      if (next.has(angleId)) next.delete(angleId);
      else next.add(angleId);
      return next;
    });
  };

  const toggleVocab = (term: string) => {
    setDeselectedVocab(prev => {
      const next = new Set(prev);
      if (next.has(term)) next.delete(term);
      else next.add(term);
      return next;
    });
  };

  const toggleQuestion = (q: string) => {
    setSelectedQuestions(prev => {
      const next = new Set(prev);
      if (next.has(q)) next.delete(q);
      else next.add(q);
      return next;
    });
  };

  const addCustomQuestion = () => {
    if (!customQuestion.trim()) return;
    setSelectedQuestions(prev => new Set(prev).add(customQuestion.trim()));
    setCustomQuestion('');
  };

  const handleProceed = () => {
    onProceed({
      angles: Array.from(selectedAngles),
      vocabulary: result.vocabulary.filter(v => !deselectedVocab.has(v)),
      questions: Array.from(selectedQuestions),
    });
  };

  const activeVocab = result.vocabulary.filter(v => !deselectedVocab.has(v));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <button
          type="button"
          onClick={onBack}
          className="text-[12px] text-gray-500 hover:text-gray-400 transition mb-3 flex items-center gap-1"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back to topic
        </button>
        <h2 className="text-xl font-bold text-gray-100">
          Creative Angles
        </h2>
        <p className="text-[14px] text-gray-400 mt-1 leading-relaxed">
          Here are {result.angles.length} ways to approach <span className="text-gray-200 font-medium">&ldquo;{topic}&rdquo;</span>.
          Select the angles that resonate, then we&apos;ll find sources.
        </p>
      </div>

      {/* Angles */}
      <div>
        <p className="text-[12px] font-medium text-gray-500 uppercase tracking-wider mb-3">
          Narrative Angles
          {selectedAngles.size > 0 && (
            <span className="text-blue-400 ml-2">({selectedAngles.size} selected)</span>
          )}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {result.angles.map(angle => (
            <AngleCard
              key={angle.angle_id}
              angle={angle}
              isSelected={selectedAngles.has(angle.angle_id)}
              onToggle={toggleAngle}
            />
          ))}
        </div>
      </div>

      {/* Vocabulary */}
      {result.vocabulary.length > 0 && (
        <div>
          <p className="text-[12px] font-medium text-gray-500 uppercase tracking-wider mb-3">
            Key Vocabulary
            <span className="text-gray-600 ml-2">(tap to remove)</span>
          </p>
          <div className="flex flex-wrap gap-2">
            {result.vocabulary.map(term => (
              <button
                key={term}
                type="button"
                onClick={() => toggleVocab(term)}
                className={`
                  text-[13px] px-3 py-1.5 rounded-full border transition-all duration-150
                  ${deselectedVocab.has(term)
                    ? 'border-gray-800 bg-gray-900/40 text-gray-600 line-through'
                    : 'border-gray-600/40 bg-gray-800/50 text-gray-300 hover:border-gray-500/60'
                  }
                `}
              >
                {term}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Key Questions */}
      {result.key_questions.length > 0 && (
        <div>
          <p className="text-[12px] font-medium text-gray-500 uppercase tracking-wider mb-3">
            Key Questions
          </p>
          <div className="space-y-2">
            {[...result.key_questions, ...Array.from(selectedQuestions).filter(q => !result.key_questions.includes(q))].map(q => (
              <label
                key={q}
                className="flex items-start gap-2.5 cursor-pointer group"
              >
                <input
                  type="checkbox"
                  checked={selectedQuestions.has(q)}
                  onChange={() => toggleQuestion(q)}
                  className="mt-1 rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500/30"
                />
                <span className="text-[14px] text-gray-300 leading-relaxed group-hover:text-gray-200 transition">
                  {q}
                </span>
              </label>
            ))}
            {/* Add custom question */}
            <div className="flex gap-2 mt-2">
              <input
                type="text"
                value={customQuestion}
                onChange={e => setCustomQuestion(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addCustomQuestion()}
                placeholder="Add your own question..."
                className="flex-1 rounded-lg border border-gray-700 bg-gray-800/60 px-3 py-2 text-[13px] text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500/50"
              />
              <button
                type="button"
                onClick={addCustomQuestion}
                disabled={!customQuestion.trim()}
                className="text-[12px] px-3 py-2 rounded-lg bg-gray-700/40 text-gray-400 hover:text-gray-300 hover:bg-gray-700/60 transition disabled:opacity-40"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Aesthetic Keywords (display only) */}
      {result.aesthetic_keywords.length > 0 && (
        <div>
          <p className="text-[12px] font-medium text-gray-500 uppercase tracking-wider mb-3">
            Aesthetic Keywords
          </p>
          <div className="flex flex-wrap gap-2">
            {result.aesthetic_keywords.map(kw => (
              <span
                key={kw}
                className="text-[12px] px-2.5 py-1 rounded bg-gray-800/50 text-gray-500 border border-gray-700/30 italic"
              >
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Proceed button */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-700/30">
        <p className="text-[12px] text-gray-600">
          {selectedAngles.size > 0
            ? `${selectedAngles.size} angle${selectedAngles.size > 1 ? 's' : ''} selected · ${activeVocab.length} terms · ${selectedQuestions.size} questions`
            : 'Select at least one angle to continue'
          }
        </p>
        <button
          type="button"
          onClick={handleProceed}
          disabled={selectedAngles.size === 0}
          className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-2.5 text-[14px] font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:from-blue-500 hover:to-blue-400 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
        >
          Find Sources
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </button>
      </div>
    </div>
  );
}
