import { LucideProps } from 'lucide-react';
import { forwardRef } from 'react';

// Component for the Bot icon
export const Bot = forwardRef<SVGSVGElement, LucideProps>(
  ({ color = 'currentColor', size = 24, ...props }, ref) => {
    return (
      <svg
        ref={ref}
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        {...props}
      >
        <path d="M12 8V4H8" />
        <rect width="16" height="12" x="4" y="8" rx="2" />
        <path d="M2 14h2" />
        <path d="M20 14h2" />
        <path d="M15 13v2" />
        <path d="M9 13v2" />
      </svg>
    );
  }
);

Bot.displayName = 'Bot';

export default Bot; 