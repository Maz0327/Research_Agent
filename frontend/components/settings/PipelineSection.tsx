/**
 * Default pipeline settings section.
 * Configures research pipeline defaults and extraction options.
 */
import SettingsSection from './SettingsSection';
import { PIPELINE_OPTIONS, PipelineType } from '../../store/settings';

interface PipelineSectionProps {
  defaultPipeline: PipelineType;
  setDefaultPipeline: (value: PipelineType) => void;
  autoExtractClaims: boolean;
  setAutoExtractClaims: (value: boolean) => void;
  maxSources: number;
  setMaxSources: (value: number) => void;
}

export function PipelineSection({
  defaultPipeline,
  setDefaultPipeline,
  autoExtractClaims,
  setAutoExtractClaims,
  maxSources,
  setMaxSources,
}: PipelineSectionProps) {
  const handleMaxSourcesChange = (value: string) => {
    const num = parseInt(value) || 25;
    setMaxSources(Math.min(50, Math.max(5, num)));
  };

  const selectedPipeline = PIPELINE_OPTIONS.find(
    (o) => o.value === defaultPipeline
  );

  return (
    <SettingsSection
      title="Default Pipeline"
      description="When creating new research jobs, use this pipeline by default."
      delay={0.3}
    >
      <div className="space-y-4">
        {/* Pipeline select */}
        <div>
          <select
            value={defaultPipeline}
            onChange={(e) => setDefaultPipeline(e.target.value as PipelineType)}
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-gray-100 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {PIPELINE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {selectedPipeline && (
            <p className="mt-2 text-sm text-gray-500">
              {selectedPipeline.description}
            </p>
          )}
        </div>

        {/* Auto-extract claims */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="autoExtractClaims"
            checked={autoExtractClaims}
            onChange={(e) => setAutoExtractClaims(e.target.checked)}
            className="h-4 w-4 rounded bg-gray-800 border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
          />
          <label
            htmlFor="autoExtractClaims"
            className="ml-3 text-sm text-gray-300"
          >
            Auto-extract claims from sources
          </label>
        </div>

        {/* Max sources */}
        <div>
          <label className="block text-sm font-medium text-gray-400">
            Maximum sources per job
          </label>
          <div className="mt-1.5 flex items-center gap-3">
            <input
              type="number"
              min={5}
              max={50}
              value={maxSources}
              onChange={(e) => handleMaxSourcesChange(e.target.value)}
              className="w-24 rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-500">(5-50)</span>
          </div>
        </div>
      </div>
    </SettingsSection>
  );
}

export default PipelineSection;
