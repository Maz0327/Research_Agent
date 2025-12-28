/**
 * Reusable wrapper component for settings sections.
 * Provides consistent styling and animations.
 */
import { motion } from 'framer-motion';
import { ReactNode } from 'react';

interface SettingsSectionProps {
  title: string;
  description?: string;
  delay?: number;
  children: ReactNode;
}

export function SettingsSection({
  title,
  description,
  delay = 0,
  children,
}: SettingsSectionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-lg"
    >
      <h2 className="mb-4 text-lg font-semibold text-gray-100">{title}</h2>
      {description && (
        <p className="mb-4 text-sm text-gray-400">{description}</p>
      )}
      {children}
    </motion.div>
  );
}

export default SettingsSection;
