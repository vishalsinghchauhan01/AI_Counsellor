import { clsx } from 'clsx'

export function Badge({ variant = 'default', className, ...props }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        variant === 'government' && 'bg-green-100 text-green-800',
        variant === 'private' && 'bg-blue-100 text-blue-800',
        variant === 'default' && 'bg-gray-100 text-gray-800',
        className
      )}
      {...props}
    />
  )
}
