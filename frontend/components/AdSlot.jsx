'use client'

/**
 * Placeholder for future ad units (e.g. Google AdSense).
 * Use the same class names when you replace with real ad markup so layout stays consistent.
 * Variants: banner (horizontal), sidebar (vertical), inline (in-feed).
 */
export default function AdSlot({ variant = 'banner', className = '' }) {
  const isBanner = variant === 'banner'
  const isSidebar = variant === 'sidebar'
  const isInline = variant === 'inline'

  return (
    <div
      className={[
        'ad-slot',
        isBanner && 'ad-slot w-full min-h-[50px] sm:min-h-[60px]',
        isSidebar && 'ad-slot w-full min-h-[250px] max-w-[160px] sm:max-w-[200px]',
        isInline && 'ad-slot ad-slot-inline w-full',
        className,
      ].filter(Boolean).join(' ')}
      data-ad-slot={variant}
      aria-hidden
    >
      {/* Replace this div with your ad script when ready */}
      <span className="opacity-70">Ad space</span>
    </div>
  )
}
