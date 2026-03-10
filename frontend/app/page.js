'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'

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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-orange-50 to-blue-50">
      <div className="text-center">
        <div className="text-4xl font-bold text-orange-600 mb-2">AI Counsellor</div>
        <div className="text-gray-500">Loading your career counsellor...</div>
      </div>
    </div>
  )
}
