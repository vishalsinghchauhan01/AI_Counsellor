'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Target, ArrowRight } from 'lucide-react'

// Stream options vary based on class selection
const STREAM_OPTIONS_SCHOOL = ['PCM', 'PCB', 'Commerce', 'Arts', 'Not decided yet']
const STREAM_OPTIONS_GRADUATE = [
  'Engineering / B.Tech',
  'Medical / MBBS / BDS',
  'Management / MBA',
  'Law / LLB',
  'Design / Architecture',
  'Arts / Humanities',
  'Commerce / CA / CS',
  'Science / M.Sc',
  'Education / B.Ed',
  'Other',
]

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
    question: 'Aapka stream / field kya hai?',
    // options are dynamic — set at render time based on class
    options: STREAM_OPTIONS_SCHOOL,
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
  const userProfile = useStore((s) => s.userProfile)
  const setIsOnboarded = useStore((s) => s.setIsOnboarded)

  const [stepIndex, setStepIndex] = useState(0)
  const [textValue, setTextValue] = useState('')

  // Dynamically pick stream options based on selected class
  const rawStep = STEPS[stepIndex]
  const step =
    rawStep.id === 'stream'
      ? {
          ...rawStep,
          question:
            userProfile.current_class === 'Graduate'
              ? 'Aapka field of study kya hai?'
              : rawStep.question,
          options:
            userProfile.current_class === 'Graduate' || userProfile.current_class === 'Other'
              ? STREAM_OPTIONS_GRADUATE
              : STREAM_OPTIONS_SCHOOL,
        }
      : rawStep
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

  const stepCount = step.type === 'welcome' ? 0 : stepIndex
  const totalSteps = STEPS.length - 1

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-amber-50/60 flex flex-col">
      {/* Progress: step dots when not on welcome */}
      {step.type !== 'welcome' && (
        <div className="flex-shrink-0 px-6 pt-6 pb-2">
          <p className="text-xs font-medium text-primary-600/80 text-center mb-3">
            Step {stepCount} of {totalSteps}
          </p>
          <div className="flex justify-center gap-2">
            {STEPS.slice(1).map((_, i) => (
              <div
                key={i}
                className={`h-1.5 flex-1 max-w-[48px] rounded-full transition-colors ${
                  i < stepCount ? 'bg-primary-500' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-6 sm:py-8">
        <div className="w-full max-w-md mx-auto">
          {step.type === 'welcome' ? (
            <div className="text-center space-y-6 animate-in fade-in duration-300">
              <div className="inline-flex w-14 h-14 rounded-2xl bg-primary-500 text-white items-center justify-center shadow-soft">
                <Target className="w-7 h-7" strokeWidth={2.5} />
              </div>
              <h1 className="text-3xl sm:text-4xl font-bold text-primary-600 tracking-tight">
                AI Counsellor
              </h1>
              <p className="text-lg text-gray-600">Apna Career Khud Chunno 🎯</p>
              <p className="text-sm text-gray-500 max-w-xs mx-auto">
                AI career counsellor for Uttarakhand students — colleges, exams, scholarships.
              </p>
              <Button
                onClick={handleWelcomeNext}
                className="mt-4 px-8 py-3 text-base rounded-xl shadow-soft inline-flex items-center gap-2"
              >
                Start
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          ) : step.type === 'text' ? (
            <div className="space-y-5">
              <h2 className="text-xl font-semibold text-gray-800 text-center leading-snug">
                {step.question}
              </h2>
              <Input
                value={textValue}
                onChange={(e) => setTextValue(e.target.value)}
                placeholder={step.placeholder}
                onKeyDown={(e) => e.key === 'Enter' && handleTextSubmit()}
                className="rounded-xl py-3 text-base"
              />
              <Button
                onClick={handleTextSubmit}
                disabled={!textValue.trim()}
                className="w-full rounded-xl py-3"
              >
                Continue
              </Button>
            </div>
          ) : (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-800 text-center leading-snug">
                {step.question}
              </h2>
              <div className="grid gap-3">
                {step.options.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => handleOption(opt)}
                    className="w-full py-3.5 px-4 rounded-xl border-2 border-gray-200 bg-white text-gray-800 font-medium hover:border-primary-300 hover:bg-primary-50/80 hover:text-primary-800 transition-all text-left shadow-soft"
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
