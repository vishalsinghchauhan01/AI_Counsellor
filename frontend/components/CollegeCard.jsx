'use client'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'

export default function CollegeCard({ college }) {
  if (!college) return null

  const type = (college.institution_type || '').toLowerCase()
  const variant = type.includes('government') ? 'government' : 'private'
  const courses = (college.courses_offered || []).slice(0, 3)
  const fees = college.fees || {}
  const feeValues = Object.values(fees)
  const feeRange =
    feeValues.length > 0
      ? `₹${Math.min(...feeValues).toLocaleString('en-IN')} - ₹${Math.max(...feeValues).toLocaleString('en-IN')}/yr`
      : '—'

  return (
    <Card className="overflow-hidden text-left">
      <CardContent className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
          <h3 className="font-semibold text-gray-900 text-sm leading-tight">
            {college.college_name}
          </h3>
          <Badge variant={variant}>{college.institution_type || '—'}</Badge>
        </div>
        {college.city && (
          <p className="text-xs text-gray-500 mb-2">{college.city}</p>
        )}
        {courses.length > 0 && (
          <p className="text-xs text-gray-600 mb-2">
            <span className="font-medium">Courses:</span>{' '}
            {courses.join(', ')}
          </p>
        )}
        <p className="text-xs text-gray-600 mb-2">
          <span className="font-medium">Fees:</span> {feeRange}
        </p>
        {college.ranking && (
          <p className="text-xs text-gray-500 mb-3">{college.ranking}</p>
        )}
        {college.website && (
          <a
            href={college.website.startsWith('http') ? college.website : `https://${college.website}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center text-xs font-medium text-primary-600 hover:text-primary-700"
          >
            Visit Website →
          </a>
        )}
      </CardContent>
    </Card>
  )
}
