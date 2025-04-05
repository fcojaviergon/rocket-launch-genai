// This is a Server Component example showing optimized images
import Image from 'next/image';

interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  priority?: boolean;
  className?: string;
}

/**
 * An example of a Server Component using Next.js optimized images
 * 
 * Benefits:
 * - Automatic image optimization
 * - Lazy loading by default
 * - Prevents Cumulative Layout Shift (CLS)
 * - Responsive sizes
 * - WebP/AVIF format conversion when supported
 */
export default function OptimizedImage({
  src,
  alt,
  width = 1200,
  height = 600,
  priority = false,
  className,
}: OptimizedImageProps) {
  return (
    <div className={`relative overflow-hidden ${className || ''}`}>
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        priority={priority}
        loading={priority ? 'eager' : 'lazy'}
        quality={80}
        className="object-cover transition-transform hover:scale-105 duration-500"
        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
      />
    </div>
  );
} 