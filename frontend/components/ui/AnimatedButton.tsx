/**
 * Button with hover scale, press feedback, and loading state.
 */
import { ReactNode, ButtonHTMLAttributes } from 'react';

interface AnimatedButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const variants = {
  primary: `
    bg-gradient-to-r from-blue-600 to-blue-500
    hover:from-blue-500 hover:to-blue-400
    text-white shadow-lg shadow-blue-500/25
    hover:shadow-blue-500/40
    border border-blue-400/20
  `,
  secondary: `
    bg-gray-800 hover:bg-gray-700
    text-gray-100 border border-gray-700
    hover:border-gray-600
  `,
  danger: `
    bg-gradient-to-r from-red-600 to-red-500
    hover:from-red-500 hover:to-red-400
    text-white shadow-lg shadow-red-500/25
    hover:shadow-red-500/40
    border border-red-400/20
  `,
  ghost: `
    bg-transparent hover:bg-gray-800/50
    text-gray-300 hover:text-gray-100
    border border-transparent
  `,
};

const sizes = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2',
};

export default function AnimatedButton({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}: AnimatedButtonProps) {
  const isDisabled = disabled || isLoading;

  return (
    <button
      className={`
        inline-flex items-center justify-center
        font-medium rounded-lg
        transition-all duration-200 ease-out
        transform hover:scale-[1.02] active:scale-[0.98]
        focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:ring-offset-2 focus:ring-offset-gray-900
        disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
        ${variants[variant]}
        ${sizes[size]}
        ${className}
      `}
      disabled={isDisabled}
      {...props}
    >
      {isLoading ? (
        <>
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Loading...</span>
        </>
      ) : (
        <>
          {leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
          {children}
          {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
        </>
      )}
    </button>
  );
}
