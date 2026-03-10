import { clsx } from 'clsx'

export function Input({ className, ...props }) {
  return (
    <input
      className={clsx(
        'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder:text-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500',
        className
      )}
      {...props}
    />
  )
}
