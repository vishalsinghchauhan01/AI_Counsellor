'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const STEPS = [
  {
    id: 'welcome',
    title: 'AI Counsellor',
    subtitle: 'Apna Career Khud Chunno 🎯',
    type: 'welcome',
  },
  {
    id: 'class',
    question: 'Aap abhi kaunsi class mein ho?',
    options: ['10th', '12th', 'Graduate', 'Other'],
    key: 'current_class',
  },
  {
    id: 'stream',
    question: 'Aapka stream kya hai?',
    options: ['PCM', 'PCB', 'Commerce', 'Arts', 'Not decided yet'],
    key: 'stream',
  },
  {
    id: 'budget',
    question: 'Aapka saath mein roughly kitna budget hai fees ke liye per year?',
    options: ['Under 50k', '50k-1.5 lakh', '1.5-3 lakh', '3 lakh+'],
    key: 'budget_per_year',
  },
  {
    id: 'location',
    question: 'Aap kahan se ho?',
    type: 'text',
    key: 'location_preference',
    placeholder: 'District ya city ka naam likhein',
  },
]

const BUDGET_MAP = {
  'Under 50k': 50000,
  '50k-1.5 lakh': 150000,
  '1.5-3 lakh': 300000,
  '3 lakh+': 500000,
}

export default function OnboardingPage() {
  const router = useRouter()
  const updateUserProfile = useStore((s) => s.updateUserProfile)
  const setIsOnboarded = useStore((s) => s.setIsOnboarded)

  const [stepIndex, setStepIndex] = useState(0)
  const [textValue, setTextValue] = useState('')

  const step = STEPS[stepIndex]
  const isLast = stepIndex === STEPS.length - 1
  const progress = ((stepIndex + 1) / STEPS.length) * 100

  const handleOption = (value) => {
    const key = step.key
    const payload = key === 'budget_per_year' ? BUDGET_MAP[value] ?? value : value
    updateUserProfile({ [key]: payload })
    if (isLast) {
      setIsOnboarded(true)
      router.push('/chat')
    } else {
      setStepIndex((i) => i + 1)
    }
  }

  const handleTextSubmit = () => {
    const val = textValue.trim()
    if (!val) return
    updateUserProfile({ [step.key]: val })
    setTextValue('')
    setIsOnboarded(true)
    router.push('/chat')
  }

  const handleWelcomeNext = () => {
    setStepIndex(1)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 flex flex-col">
      {/* Progress bar */}
      <div className="h-1 bg-gray-200">
        <div
          className="h-full bg-orange-500 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-8">
        <div className="w-full max-w-md mx-auto">
          {step.type === 'welcome' ? (
            <div className="text-center space-y-6 animate-in fade-in duration-300">
              <h1 className="text-4xl font-bold text-orange-600">AI Counsellor</h1>
              <p className="text-lg text-gray-600">Apna Career Khud Chunno 🎯</p>
              <p className="text-sm text-gray-500">
                AI career counsellor for Uttarakhand students — colleges, exams, scholarships.
              </p>
              <Button onClick={handleWelcomeNext} className="mt-4 px-8 py-3 text-base">
                Start
              </Button>
            </div>
          ) : step.type === 'text' ? (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold text-gray-800 text-center">
                {step.question}
              </h2>
              <Input
                value={textValue}
                onChange={(e) => setTextValue(e.target.value)}
                placeholder={step.placeholder}
                onKeyDown={(e) => e.key === 'Enter' && handleTextSubmit()}
              />
              <Button
                onClick={handleTextSubmit}
                disabled={!textValue.trim()}
                className="w-full"
              >
                Continue
              </Button>
            </div>
          ) : (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-800 text-center">
                {step.question}
              </h2>
              <div className="grid gap-3">
                {step.options.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => handleOption(opt)}
                    className="w-full py-3 px-4 rounded-xl border-2 border-orange-200 bg-white text-gray-800 font-medium hover:border-orange-400 hover:bg-orange-50 transition-colors text-left"
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
