'use client'
import { useState } from 'react'
import { Target, ExternalLink, Volume2, ChevronDown, ChevronUp, Database } from 'lucide-react'

// ── Inline formatting ──────────────────────────────────────────────
// Combined regex: markdown links | bold | italic | inline code | plain URLs
const INLINE_RE =
  /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\))|(\*\*([^*]+)\*\*)|(\*([^*]+)\*)|(`)([^`]+)(`)|(https?:\/\/[^\s<>)\]]+)/g

function formatInline(text, lineIdx) {
  const tokens = []
  let lastIndex = 0
  let match

  INLINE_RE.lastIndex = 0
  while ((match = INLINE_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push(text.slice(lastIndex, match.index))
    }

    if (match[1]) {
      // Markdown link [text](url)
      tokens.push(
        <a
          key={`${lineIdx}-l-${match.index}`}
          href={match[3]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary-600 hover:text-primary-700 underline underline-offset-2 inline-flex items-center gap-0.5"
        >
          {match[2]}
          <ExternalLink className="inline w-3 h-3 flex-shrink-0" />
        </a>
      )
    } else if (match[4]) {
      // Bold **text**
      tokens.push(
        <strong key={`${lineIdx}-b-${match.index}`} className="font-semibold text-gray-900">
          {match[5]}
        </strong>
      )
    } else if (match[6]) {
      // Italic *text*
      tokens.push(<em key={`${lineIdx}-i-${match.index}`}>{match[7]}</em>)
    } else if (match[8]) {
      // Inline code `text`
      tokens.push(
        <code
          key={`${lineIdx}-c-${match.index}`}
          className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-[13px] font-mono"
        >
          {match[9]}
        </code>
      )
    } else if (match[11]) {
      // Plain URL
      tokens.push(
        <a
          key={`${lineIdx}-u-${match.index}`}
          href={match[11]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary-600 hover:text-primary-700 underline underline-offset-2 inline-flex items-center gap-0.5 break-all"
        >
          {match[11].replace(/^https?:\/\/(www\.)?/, '').slice(0, 40)}
          <ExternalLink className="inline w-3 h-3 flex-shrink-0" />
        </a>
      )
    }
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) tokens.push(text.slice(lastIndex))
  return tokens.length > 0 ? tokens : [text]
}

// ── Block-level formatting ─────────────────────────────────────────
function formatContent(text) {
  if (!text) return null

  const lines = text.split('\n')
  const elements = []
  let listBuffer = []
  let listType = null // 'ul' or 'ol'

  function flushList() {
    if (listBuffer.length === 0) return
    const ListTag = listType === 'ol' ? 'ol' : 'ul'
    const listClass =
      listType === 'ol'
        ? 'list-decimal list-inside space-y-3 my-2 ml-0.5'
        : 'list-disc list-inside space-y-1 my-1.5 ml-1'
    elements.push(
      <ListTag key={`list-${elements.length}`} className={listClass}>
        {listBuffer.map((item, j) => {
          const parts = item.split('\n')
          return (
            <li key={j} className="text-[15px] leading-relaxed">
              {formatInline(parts[0], `li-${elements.length}-${j}`)}
              {parts.length > 1 && (
                <ul className="list-disc list-inside ml-5 mt-1 space-y-0.5 text-sm">
                  {parts.slice(1).map((sub, k) => (
                    <li key={k} className="text-gray-700 leading-relaxed">
                      {formatInline(sub.replace(/^[•·]\s*/, ''), `sub-${elements.length}-${j}-${k}`)}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          )
        })}
      </ListTag>
    )
    listBuffer = []
    listType = null
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    // Empty line — check if we should continue an ordered list
    if (!trimmed) {
      if (listType === 'ol') {
        // Look ahead: if next non-empty line is also a numbered item, continue
        let nextIdx = i + 1
        while (nextIdx < lines.length && !lines[nextIdx].trim()) nextIdx++
        if (nextIdx < lines.length && /^\d+\.\s+/.test(lines[nextIdx].trim())) {
          continue
        }
      }
      flushList()
      elements.push(<div key={`sp-${i}`} className="h-1.5" />)
      continue
    }

    // Horizontal rule
    if (/^[-*_]{3,}$/.test(trimmed)) {
      flushList()
      elements.push(<hr key={`hr-${i}`} className="my-3 border-gray-200" />)
      continue
    }

    // Headers: ### H3, ## H2, # H1
    const headerMatch = trimmed.match(/^(#{1,3})\s+(.+)$/)
    if (headerMatch) {
      flushList()
      const level = headerMatch[1].length
      const content = formatInline(headerMatch[2], `h-${i}`)
      if (level === 1)
        elements.push(
          <h3 key={`h-${i}`} className="text-base font-bold text-gray-900 mt-3 mb-1.5 border-b border-gray-100 pb-1">
            {content}
          </h3>
        )
      else if (level === 2)
        elements.push(
          <h4 key={`h-${i}`} className="text-[15px] font-bold text-gray-900 mt-2.5 mb-1">
            {content}
          </h4>
        )
      else
        elements.push(
          <h5 key={`h-${i}`} className="text-[15px] font-semibold text-gray-800 mt-2 mb-0.5">
            {content}
          </h5>
        )
      continue
    }

    // Sub-bullet under an ordered list item → append to last item
    const bulletMatch = trimmed.match(/^[-*•·]\s+(.+)$/)
    if (bulletMatch && listType === 'ol' && listBuffer.length > 0) {
      listBuffer[listBuffer.length - 1] += '\n· ' + bulletMatch[1]
      continue
    }

    // Unordered list: - item, * item, • item
    if (bulletMatch) {
      if (listType !== 'ul') flushList()
      listType = 'ul'
      listBuffer.push(bulletMatch[1])
      continue
    }

    // Ordered list: 1. item, 2. item
    const olMatch = trimmed.match(/^\d+\.\s+(.+)$/)
    if (olMatch) {
      if (listType !== 'ol') flushList()
      listType = 'ol'
      listBuffer.push(olMatch[1])
      continue
    }

    // Regular paragraph
    flushList()
    elements.push(
      <p key={`p-${i}`} className="text-[15px] leading-relaxed text-gray-800">
        {formatInline(trimmed, i)}
      </p>
    )
  }

  flushList()
  return elements
}

// ── Source type labels ─────────────────────────────────────────────
const SOURCE_LABELS = {
  college: 'College',
  career: 'Career',
  exam: 'Exam',
  scholarship: 'Scholarship',
  stream_guide: 'Stream Guide',
  study_plan: 'Study Plan',
}

const SOURCE_COLORS = {
  college: 'bg-blue-50 text-blue-700 border-blue-200',
  career: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  exam: 'bg-amber-50 text-amber-700 border-amber-200',
  scholarship: 'bg-purple-50 text-purple-700 border-purple-200',
  stream_guide: 'bg-pink-50 text-pink-700 border-pink-200',
  study_plan: 'bg-cyan-50 text-cyan-700 border-cyan-200',
}

// ── Sources Section ───────────────────────────────────────────────
function SourcesList({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-2 pt-2 border-t border-gray-100">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        <Database className="w-3 h-3" />
        {sources.length} source{sources.length > 1 ? 's' : ''} used
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {open && (
        <div className="flex flex-wrap gap-1.5 mt-1.5">
          {sources.map((s, i) => (
            <span
              key={i}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${
                SOURCE_COLORS[s.source_type] || 'bg-gray-50 text-gray-600 border-gray-200'
              }`}
            >
              {SOURCE_LABELS[s.source_type] || s.source_type}
              <span className="opacity-70">·</span>
              <span className="max-w-[120px] truncate">{s.name}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Message Bubble ─────────────────────────────────────────────────
export default function MessageBubble({ message, onSpeak, msgIndex }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex w-full gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-primary-500 flex items-center justify-center text-white shadow-soft mt-0.5">
          <Target className="w-4 h-4" strokeWidth={2.5} />
        </div>
      )}
      <div
        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-primary-500 text-white rounded-tr-md shadow-soft'
            : 'bg-white border border-[var(--border)] shadow-soft text-gray-800 rounded-tl-md'
        }`}
      >
        <div className="break-words space-y-0.5">
          {isUser ? (
            <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            formatContent(message.content)
          )}
        </div>
        {!isUser && message.content && (
          <div className="flex items-center gap-3 mt-2.5">
            <button
              type="button"
              onClick={() => onSpeak(message.content, msgIndex)}
              className="flex items-center gap-1.5 text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
              aria-label="Listen to this message"
            >
              <span className="inline-flex w-5 h-5 rounded-full bg-primary-100 items-center justify-center text-primary-600">
                <Volume2 className="w-3 h-3" />
              </span>
              Listen
            </button>
          </div>
        )}
        {!isUser && <SourcesList sources={message.sources} />}
      </div>
    </div>
  )
}
