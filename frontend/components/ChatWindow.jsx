'use client'
import React, { useEffect, useRef, useState } from 'react'
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
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
        {messages.map((msg, i) => (
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
        ))}
        {isLoading && (
          <div className="flex gap-2">
            <div className="w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center text-white text-sm font-bold">
              U
            </div>
            <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-tl-md px-4 py-3 flex gap-1">
              <span className="w-2 h-2 rounded-full bg-orange-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 rounded-full bg-orange-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 rounded-full bg-orange-400 animate-bounce" style={{ animationDelay: '300ms' }} />
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
