import { clsx } from 'clsx'

export function Card({ className, ...props }) {
  return (
    <div
      className={clsx(
        'rounded-xl border border-[var(--border)] bg-white shadow-soft',
        className
      )}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }) {
  return <div className={clsx('px-4 py-3 border-b border-gray-100', className)} {...props} />
}

export function CardContent({ className, ...props }) {
  return <div className={clsx('p-4', className)} {...props} />
}
