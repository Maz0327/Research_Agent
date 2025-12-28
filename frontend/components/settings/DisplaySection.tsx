/**
 * Display settings section.
 * Controls UI preferences like pagination and sorting.
 */
import SettingsSection from './SettingsSection';
import { SORT_OPTIONS, SortOrder } from '../../store/settings';

interface DisplaySectionProps {
  jobsPerPage: number;
  setJobsPerPage: (value: number) => void;
  defaultSort: SortOrder;
  setDefaultSort: (value: SortOrder) => void;
  showProgressDetails: boolean;
  setShowProgressDetails: (value: boolean) => void;
}

export function DisplaySection({
  jobsPerPage,
  setJobsPerPage,
  defaultSort,
  setDefaultSort,
  showProgressDetails,
  setShowProgressDetails,
}: DisplaySectionProps) {
  const handleJobsPerPageChange = (value: string) => {
    const num = parseInt(value) || 10;
    setJobsPerPage(Math.min(25, Math.max(5, num)));
  };

  return (
    <SettingsSection title="Display" delay={0.5}>
      <div className="space-y-4">
        {/* Jobs per page */}
        <div>
          <label className="block text-sm font-medium text-gray-400">
            Jobs per page
          </label>
          <div className="mt-1.5 flex items-center gap-3">
            <input
              type="number"
              min={5}
              max={25}
              value={jobsPerPage}
              onChange={(e) => handleJobsPerPageChange(e.target.value)}
              className="w-24 rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-500">(5-25)</span>
          </div>
        </div>

        {/* Default sort */}
        <div>
          <label className="block text-sm font-medium text-gray-400">
            Default sort
          </label>
          <select
            value={defaultSort}
            onChange={(e) => setDefaultSort(e.target.value as SortOrder)}
            className="mt-1.5 w-48 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-gray-100 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Show progress details */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="showProgressDetails"
            checked={showProgressDetails}
            onChange={(e) => setShowProgressDetails(e.target.checked)}
            className="h-4 w-4 rounded bg-gray-800 border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
          />
          <label
            htmlFor="showProgressDetails"
            className="ml-3 text-sm text-gray-300"
          >
            Show detailed progress during jobs
          </label>
        </div>
      </div>
    </SettingsSection>
  );
}

export default DisplaySection;
