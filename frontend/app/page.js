'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { Target } from 'lucide-react'

export default function Home() {
  const router = useRouter()
  const isOnboarded = useStore((state) => state.isOnboarded)

  useEffect(() => {
    if (isOnboarded) {
      router.push('/chat')
    } else {
      router.push('/onboarding')
    }
  }, [isOnboarded, router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-orange-50/50">
      <div className="text-center px-6">
        <div className="inline-flex w-16 h-16 rounded-2xl bg-primary-500 text-white items-center justify-center shadow-soft-lg mb-6 animate-in fade-in duration-500">
          <Target className="w-8 h-8" strokeWidth={2.5} />
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-primary-600 mb-2 tracking-tight">
          AI Counsellor
        </h1>
        <p className="text-primary-700/80 text-sm sm:text-base mb-6">
          Apna Career Khud Chunno
        </p>
        <div className="flex justify-center gap-1">
          <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  )
}
