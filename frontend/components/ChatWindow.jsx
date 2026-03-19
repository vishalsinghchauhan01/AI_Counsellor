'use client'
import React, { useEffect, useRef, useState } from 'react'
import { Target } from 'lucide-react'
import MessageBubble from './MessageBubble'
import CollegeCard from './CollegeCard'
import CareerRoadmap from './CareerRoadmap'
import { getAllColleges } from '@/lib/api'

const COLLEGE_NAMES = [
  'IIT Roorkee',
  'AIIMS',
  'NIT UK',
  'IIM Kashipur',
  'UPES',
  'Graphic Era',
  'Doon University',
  'GBPUAT',
  'HNB Garhwal',
  'Kumaun University',
  'DIT University',
  'ICFAI',
  'Patanjali',
  'SRHU',
  'Uttaranchal University',
  'SDSUV',
  'Quantum',
  'FRI',
  'GKV',
  'DBUU',
  'IMS Unison',
  'SSJU',
  'UTU',
  'GEHU',
  'Motherhood University',
  'DSVV',
  'SGRRU',
]

function extractCollegeNamesFromText(text) {
  const found = []
  const lower = (text || '').toLowerCase()
  for (const name of COLLEGE_NAMES) {
    if (lower.includes(name.toLowerCase())) found.push(name)
  }
  return found
}

function extractRoadmapSteps(text) {
  const lower = (text || '').toLowerCase()
  if (!text || (!lower.includes('career path') && !lower.includes('roadmap'))) return []
  const lines = text.split(/\n/).filter((l) => l.trim())
  const steps = lines
    .filter((l) => /^\d+\.|^[-*]|^•|path after|step \d/i.test(l) || (l.length < 120 && l.length > 10))
    .slice(0, 6)
    .map((l) => l.replace(/^\d+\.\s*|^[-*•]\s*/i, '').trim())
  return steps.length > 0 ? steps : []
}

export default function ChatWindow({
  messages,
  isLoading,
  onSpeak,
  collegesCache,
  setCollegesCache,
}) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const resolveCollegesForMessage = async (content) => {
    const names = extractCollegeNamesFromText(content)
    if (names.length === 0) return []
    const cacheKey = names.sort().join(',')
    if (collegesCache[cacheKey]) return collegesCache[cacheKey]
    try {
      const { colleges } = await getAllColleges()
      const matched = colleges.filter((c) =>
        names.some((n) => (c.college_name || '').toLowerCase().includes(n.toLowerCase()))
      )
      if (setCollegesCache) setCollegesCache((prev) => ({ ...prev, [cacheKey]: matched }))
      return matched
    } catch {
      return []
    }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden bg-gradient-to-b from-gray-50/80 to-[var(--background)]">
      <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-4 space-y-5 max-w-3xl mx-auto w-full">
        {messages.map((msg, i) => {
          // Skip the empty assistant placeholder — the loading dots below handle it
          if (msg.role === 'assistant' && !msg.content) return null
          return (
            <div key={i}>
              <MessageBubble message={msg} onSpeak={onSpeak} />
              {msg.role === 'assistant' && msg.content && (
                <>
                  <CollegeCardsForMessage
                    content={msg.content}
                    collegesCache={collegesCache}
                    setCollegesCache={setCollegesCache}
                    resolveCollegesForMessage={resolveCollegesForMessage}
                  />
                  <CareerRoadmap steps={extractRoadmapSteps(msg.content)} />
                </>
              )}
            </div>
          )
        })}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary-500 flex items-center justify-center text-white shadow-soft flex-shrink-0">
              <Target className="w-4 h-4" strokeWidth={2.5} />
            </div>
            <div className="bg-white border border-[var(--border)] shadow-soft rounded-2xl rounded-tl-md px-5 py-3.5 flex gap-1.5 items-center">
              <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
      </div>
      <div ref={bottomRef} />
    </div>
  )
}

function CollegeCardsForMessage({
  content,
  collegesCache,
  setCollegesCache,
  resolveCollegesForMessage,
}) {
  const [colleges, setColleges] = useState([])
  const [done, setDone] = useState(false)
  const names = extractCollegeNamesFromText(content)
  const cacheKey = names.sort().join(',')

  useEffect(() => {
    if (names.length === 0) {
      setDone(true)
      return
    }
    if (collegesCache[cacheKey]) {
      setColleges(collegesCache[cacheKey])
      setDone(true)
      return
    }
    let cancelled = false
    resolveCollegesForMessage(content).then((list) => {
      if (!cancelled) {
        setColleges(list)
        setDone(true)
      }
    })
    return () => { cancelled = true }
  }, [content, cacheKey])

  if (!done || colleges.length === 0) return null

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 pl-10">
      {colleges.slice(0, 4).map((c, i) => (
        <CollegeCard key={c.college_name + i} college={c} />
      ))}
    </div>
  )
}
