'use client'

// Simple markdown-like: bold (**text**), line breaks
function formatContent(text) {
  if (!text) return ''
  return text
    .split(/\n/g)
    .map((line) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g)
      return parts.map((part) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={Math.random()}>{part.slice(2, -2)}</strong>
        }
        return part
      })
    })
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
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center text-white text-sm font-bold">
          U
        </div>
      )}
      <div
        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-2.5 ${
          isUser
            ? 'bg-orange-500 text-white rounded-tr-md'
            : 'bg-white border border-gray-100 shadow-sm text-gray-800 rounded-tl-md'
        }`}
      >
        <div className="text-sm whitespace-pre-wrap break-words">
          {formatContent(message.content)}
        </div>
        {!isUser && message.content && (
          <button
            type="button"
            onClick={() => onSpeak(message.content)}
            className="mt-2 flex items-center gap-1 text-xs text-orange-600 hover:text-orange-700"
            aria-label="Play message"
          >
            <span className="inline-block w-4 h-4 rounded-full bg-orange-100 flex items-center justify-center">
              ▶
            </span>
            Listen
          </button>
        )}
      </div>
    </div>
  )
}
