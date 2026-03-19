'use client'
import { Card, CardContent } from '@/components/ui/card'

export default function CareerRoadmap({ steps = [] }) {
  if (!steps || steps.length === 0) return null

  return (
    <Card className="my-2 text-left">
      <CardContent className="p-4">
        <h4 className="font-semibold text-gray-900 text-sm mb-3">Career Path</h4>
        <ol className="space-y-2">
          {steps.map((step, i) => (
            <li key={i} className="flex gap-2 text-sm">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-medium">
                {i + 1}
              </span>
              <span className="text-gray-700">{step}</span>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  )
}
