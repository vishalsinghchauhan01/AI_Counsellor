'use client'
import { Target, ExternalLink } from 'lucide-react'

// Regex patterns for inline formatting
const MD_LINK = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g // [text](url)
const PLAIN_URL = /(https?:\/\/[^\s<>)\]]+)/g // bare URLs
const BOLD = /\*\*([^*]+)\*\*/g // **bold**

// Tokenize a single line into React elements (links, bold, plain text)
function formatLine(line, lineIdx) {
  // First pass: split by markdown links [text](url)
  const tokens = []
  let lastIndex = 0
  let match

  // Combined regex: markdown links OR bold OR plain URLs
  const combined = /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\))|(\*\*([^*]+)\*\*)|(https?:\/\/[^\s<>)\]]+)/g
  while ((match = combined.exec(line)) !== null) {
    // Push preceding plain text
    if (match.index > lastIndex) {
      tokens.push(line.slice(lastIndex, match.index))
    }

    if (match[1]) {
      // Markdown link: [text](url)
      tokens.push(
        <a
          key={`${lineIdx}-link-${match.index}`}
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
      // Bold: **text**
      tokens.push(<strong key={`${lineIdx}-b-${match.index}`}>{match[5]}</strong>)
    } else if (match[6]) {
      // Plain URL
      tokens.push(
        <a
          key={`${lineIdx}-url-${match.index}`}
          href={match[6]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary-600 hover:text-primary-700 underline underline-offset-2 inline-flex items-center gap-0.5 break-all"
        >
          {match[6].replace(/^https?:\/\/(www\.)?/, '').slice(0, 40)}
          <ExternalLink className="inline w-3 h-3 flex-shrink-0" />
        </a>
      )
    }
    lastIndex = match.index + match[0].length
  }

  // Remaining plain text
  if (lastIndex < line.length) {
    tokens.push(line.slice(lastIndex))
  }

  return tokens.length > 0 ? tokens : [line]
}

function formatContent(text) {
  if (!text) return ''
  return text
    .split(/\n/g)
    .map((line, i) => formatLine(line, i))
    .reduce((acc, line, i) => {
      if (i > 0) acc.push(<br key={`br-${i}`} />)
      acc.push(<span key={i}>{line}</span>)
      return acc
    }, [])
}

export default function MessageBubble({ message, onSpeak }) {
  const isUser = message.role === 'user'

  return (
    <div
      className={`flex w-full gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {!isUser && (
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-primary-500 flex items-center justify-center text-white shadow-soft">
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
        <div className="text-[15px] leading-relaxed whitespace-pre-wrap break-words">
          {formatContent(message.content)}
        </div>
        {!isUser && message.content && (
          <button
            type="button"
            onClick={() => onSpeak(message.content)}
            className="mt-2.5 flex items-center gap-1.5 text-xs text-primary-600 hover:text-primary-700 font-medium"
            aria-label="Play message"
          >
            <span className="inline-flex w-5 h-5 rounded-full bg-primary-100 items-center justify-center text-primary-600">
              ▶
            </span>
            Listen
          </button>
        )}
      </div>
    </div>
  )
}
