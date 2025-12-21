/**
 * Dark mode card with subtle glow effect on hover.
 */
import { ReactNode } from 'react';

interface GlowCardProps {
  children: ReactNode;
  className?: string;
  glowColor?: 'blue' | 'purple' | 'green' | 'orange';
  onClick?: () => void;
  as?: 'div' | 'button';
}

const glowColors = {
  blue: 'hover:border-blue-500/50 hover:shadow-blue-500/20',
  purple: 'hover:border-purple-500/50 hover:shadow-purple-500/20',
  green: 'hover:border-green-500/50 hover:shadow-green-500/20',
  orange: 'hover:border-orange-500/50 hover:shadow-orange-500/20',
};

export default function GlowCard({
  children,
  className = '',
  glowColor = 'blue',
  onClick,
  as = 'div',
}: GlowCardProps) {
  const baseClasses = `
    rounded-xl border border-gray-800 bg-gray-900/80 backdrop-blur-sm
    shadow-lg transition-all duration-300 ease-out
    ${glowColors[glowColor]}
    hover:shadow-lg hover:-translate-y-0.5
  `;

  const Component = as;

  return (
    <Component
      className={`${baseClasses} ${className}`}
      onClick={onClick}
      type={as === 'button' ? 'button' : undefined}
    >
      {children}
    </Component>
  );
}
