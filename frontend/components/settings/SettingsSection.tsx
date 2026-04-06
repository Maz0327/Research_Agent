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
  /** Optional icon rendered before the title */
  icon?: ReactNode;
  children: ReactNode;
}

export function SettingsSection({
  title,
  description,
  delay = 0,
  icon,
  children,
}: SettingsSectionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-xl border border-border bg-background p-6 shadow-lg"
    >
      <h2 className="mb-4 text-lg font-semibold text-foreground flex items-center gap-2">
        {icon && <span className="flex-shrink-0">{icon}</span>}
        {title}
      </h2>
      {description && (
        <p className="mb-4 text-sm text-muted-foreground">{description}</p>
      )}
      {children}
    </motion.div>
  );
}

export default SettingsSection;
