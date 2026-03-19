/**
 * shadcn/ui Skeleton component — extended for backward compatibility.
 * Original pages/ components pass height/width props as inline styles;
 * the shadcn version accepts className only. This version supports both.
 */
import { cn } from "@/lib/utils"

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Height in pixels (number) or any CSS value (string) — backward compat */
  height?: number | string;
  /** Width in pixels (number) or any CSS value (string) — backward compat */
  width?: number | string;
}

function Skeleton({ className, height, width, style, ...props }: SkeletonProps) {
  const inlineStyle: React.CSSProperties = {
    ...(height !== undefined
      ? { height: typeof height === 'number' ? `${height}px` : height }
      : {}),
    ...(width !== undefined
      ? { width: typeof width === 'number' ? `${width}px` : width }
      : {}),
    ...style,
  };

  return (
    <div
      className={cn("animate-pulse rounded-md bg-primary/10", className)}
      style={Object.keys(inlineStyle).length ? inlineStyle : undefined}
      {...props}
    />
  )
}

export { Skeleton }

// Default export for backward compatibility with components/ui/index.ts
export default Skeleton
