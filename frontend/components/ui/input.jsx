import { forwardRef } from 'react'
import { clsx } from 'clsx'

export const Input = forwardRef(function Input({ className, ...props }, ref) {
  return (
    <input
      ref={ref}
      className={clsx(
        'w-full rounded-xl border border-[var(--border)] px-3 py-2 text-sm shadow-soft placeholder:text-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500',
        className
      )}
      {...props}
    />
  )
})
