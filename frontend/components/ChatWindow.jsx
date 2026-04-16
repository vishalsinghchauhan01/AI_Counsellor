'use client'
import React, { useEffect, useRef, useState } from 'react'
import { Target } from 'lucide-react'
import MessageBubble from './MessageBubble'
import CollegeCard from './CollegeCard'
import { searchColleges } from '@/lib/api'


export default function ChatWindow({
  messages,
  isLoading,
  onSpeak,
  collegesCache,
  setCollegesCache,
  messageSources,
}) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="flex flex-col flex-1 overflow-hidden bg-gradient-to-b from-gray-50/80 to-[var(--background)]">
      <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-4 space-y-5 max-w-3xl mx-auto w-full">
        {messages.map((msg, i) => {
          // Skip the empty assistant placeholder — the loading dots below handle it
          if (msg.role === 'assistant' && !msg.content) return null
          const sources = (messageSources || {})[i]
          const collegeNames = sources?.colleges || []
          return (
            <div key={i}>
              <MessageBubble message={msg} onSpeak={onSpeak} />
              {msg.role === 'assistant' && msg.content && (
                <>
                  {collegeNames.length > 0 && (
                    <CollegeCardsForMessage
                      collegeNames={collegeNames}
                      collegesCache={collegesCache}
                      setCollegesCache={setCollegesCache}
                    />
                  )}
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
  collegeNames,
  collegesCache,
  setCollegesCache,
}) {
  const [colleges, setColleges] = useState([])
  const [done, setDone] = useState(false)
  const cacheKey = [...collegeNames].sort().join(',')

  useEffect(() => {
    if (collegeNames.length === 0) {
      setDone(true)
      return
    }
    if (collegesCache[cacheKey]) {
      setColleges(collegesCache[cacheKey])
      setDone(true)
      return
    }
    let cancelled = false
    // Fetch each college by name using the search endpoint
    Promise.all(
      collegeNames.map((name) =>
        searchColleges({ query: name }).then((res) => res.colleges || []).catch(() => [])
      )
    ).then((results) => {
      if (cancelled) return
      // Flatten and deduplicate by college_name
      const seen = new Set()
      const matched = []
      for (const list of results) {
        for (const c of list) {
          if (!seen.has(c.college_name)) {
            seen.add(c.college_name)
            matched.push(c)
          }
        }
      }
      setColleges(matched)
      if (setCollegesCache) setCollegesCache((prev) => ({ ...prev, [cacheKey]: matched }))
      setDone(true)
    })
    return () => { cancelled = true }
  }, [cacheKey])

  if (!done || colleges.length === 0) return null

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 pl-10">
      {colleges.slice(0, 4).map((c, i) => (
        <CollegeCard key={c.college_name + i} college={c} />
      ))}
    </div>
  )
}
