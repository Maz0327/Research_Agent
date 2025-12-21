/**
 * Gradient text component for headings and emphasis.
 */
import { ReactNode } from 'react';

interface GradientTextProps {
  children: ReactNode;
  variant?: 'blue-purple' | 'green-blue' | 'orange-red' | 'purple-pink';
  as?: 'span' | 'h1' | 'h2' | 'h3' | 'h4' | 'p';
  className?: string;
  animate?: boolean;
}

const gradients = {
  'blue-purple': 'from-blue-400 via-blue-500 to-purple-500',
  'green-blue': 'from-green-400 via-cyan-500 to-blue-500',
  'orange-red': 'from-orange-400 via-red-500 to-pink-500',
  'purple-pink': 'from-purple-400 via-pink-500 to-rose-500',
};

export default function GradientText({
  children,
  variant = 'blue-purple',
  as = 'span',
  className = '',
  animate = false,
}: GradientTextProps) {
  const Component = as;

  return (
    <Component
      className={`
        bg-gradient-to-r ${gradients[variant]}
        bg-clip-text text-transparent
        ${animate ? 'animate-gradient bg-[length:200%_auto]' : ''}
        ${className}
      `}
    >
      {children}
    </Component>
  );
}
