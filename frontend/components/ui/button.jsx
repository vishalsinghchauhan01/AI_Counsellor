import { clsx } from 'clsx'

export function Button({ className, children, ...props }) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50',
        'bg-primary-500 text-white hover:bg-primary-600 active:bg-primary-700 shadow-soft',
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
}
