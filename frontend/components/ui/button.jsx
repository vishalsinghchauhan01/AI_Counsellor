import { clsx } from 'clsx'

export function Button({ className, children, ...props }) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 disabled:opacity-50',
        'bg-orange-500 text-white hover:bg-orange-600 active:bg-orange-700',
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
}
