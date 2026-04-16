'use client'
import { useState, useEffect, useRef } from 'react'
import { useStore } from '@/lib/store'
import { getOnboardingMessage, sendChatMessage, speechToText } from '@/lib/api'
import ChatWindow from '@/components/ChatWindow'
import VoiceButton from '@/components/VoiceButton'
import AdSlot from '@/components/AdSlot'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Menu, Send, RotateCcw, Square, Target, ChevronDown, ChevronUp, Trash2 } from 'lucide-react'

const ERROR_MSG =
  'Abhi server se connect nahi ho pa raha. Please thodi der baad try karein.'

const SUGGESTED_PROMPTS = [
  'Best engineering colleges in Uttarakhand',
  'Scholarships for 12th passed students',
  'Career options after PCB',
  'JEE preparation tips',
]

let welcomeLoadStarted = false

export default function ChatPage() {
  const {
    messages,
    addMessage,
    updateLastMessage,
    setLoading,
    isLoading,
    userProfile,
    clearMessages,
    resetAll,
  } = useStore()

  const [input, setInput] = useState('')
  const [collegesCache, setCollegesCache] = useState({})
  const [initialLoad, setInitialLoad] = useState(true)
  const [menuOpen, setMenuOpen] = useState(false)
  const [suggestionsOpen, setSuggestionsOpen] = useState(true)
  const [messageSources, setMessageSources] = useState({})
  const abortRef = useRef(null)
  const loadWelcomeMessage = () => {
    if (welcomeLoadStarted) return
    welcomeLoadStarted = true
    setLoading(true)
    getOnboardingMessage()
      .then((msg) => {
        addMessage({ role: 'assistant', content: msg })
      })
      .catch(() => {
        addMessage({ role: 'assistant', content: ERROR_MSG })
      })
      .finally(() => setLoading(false))
  }

  // Load one English welcome message on first visit to chat
  useEffect(() => {
    if (initialLoad && messages.length === 0) {
      setInitialLoad(false)
      loadWelcomeMessage()
    }
  }, [initialLoad, messages.length])

  const handleNewChat = () => {
    setMenuOpen(false)
    clearMessages()
    setCollegesCache({})
    setMessageSources({})
    welcomeLoadStarted = false
    loadWelcomeMessage()
  }

  const handleStartFresh = () => {
    setMenuOpen(false)
    resetAll()
    setCollegesCache({})
    setMessageSources({})
    welcomeLoadStarted = false
    loadWelcomeMessage()
  }

  const handleCancel = () => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    setLoading(false)
  }

  const sendMessage = async (textToSend) => {
    const text = (textToSend ?? input).trim()
    if (!text || isLoading) return

    setInput('')
    addMessage({ role: 'user', content: text })
    setLoading(true)
    addMessage({ role: 'assistant', content: '' })

    abortRef.current = new AbortController()
    // The assistant message will be at this index after the user message is added
    const assistantMsgIndex = messages.length + 1

    try {
      const historyForApi = messages.slice(0, -1)
      await sendChatMessage(
        text,
        historyForApi,
        {
          current_class: userProfile.current_class,
          stream: userProfile.stream,
          career_interest: userProfile.career_interest,
          budget_per_year: userProfile.budget_per_year,
          category: userProfile.category,
          location_preference: userProfile.location_preference,
          willing_to_relocate: userProfile.willing_to_relocate,
        },
        (chunk) => updateLastMessage(chunk),
        () => {
          setLoading(false)
          abortRef.current = null
        },
        {
          signal: abortRef.current.signal,
          onSources: (sources) => {
            setMessageSources((prev) => ({ ...prev, [assistantMsgIndex]: sources }))
          },
        }
      )
    } catch (err) {
      if (err?.name === 'AbortError') {
        // User cancelled - keep partial response, just stop loading
        setLoading(false)
        abortRef.current = null
        return
      }
      updateLastMessage(ERROR_MSG)
      setLoading(false)
      abortRef.current = null
    }
  }

  const handleSend = () => sendMessage()
  const handleSuggestedPrompt = (prompt) => sendMessage(prompt)

  const handleVoiceResult = async (audioBlob) => {
    try {
      const text = await speechToText(audioBlob)
      if (text && text.trim()) {
        setInput((prev) => (prev ? `${prev} ${text}` : text))
      }
    } catch {
      addMessage({ role: 'assistant', content: ERROR_MSG })
    }
  }

  const [speakingId, setSpeakingId] = useState(null)

  const handleSpeak = (text, msgIndex) => {
    // If already speaking, stop
    if (window.speechSynthesis.speaking || speakingId === msgIndex) {
      window.speechSynthesis.cancel()
      setSpeakingId(null)
      return
    }

    window.speechSynthesis.cancel() // stop any previous speech
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'en-IN' // Indian English — handles Hinglish well
    utterance.rate = 1.0
    utterance.pitch = 1.0

    // Prefer a natural-sounding English (India) voice
    const voices = window.speechSynthesis.getVoices()
    const preferred = voices.find((v) => v.lang === 'en-IN') ||
                      voices.find((v) => v.lang.startsWith('en'))
    if (preferred) utterance.voice = preferred

    utterance.onend = () => setSpeakingId(null)
    utterance.onerror = () => setSpeakingId(null)

    setSpeakingId(msgIndex)
    window.speechSynthesis.speak(utterance)
  }

  return (
    <div className="flex flex-col h-screen bg-[var(--background)]">
      {/* Header */}
      <header className="flex-shrink-0 flex items-center justify-between px-4 py-3 bg-white border-b border-[var(--border)] shadow-soft relative">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            className="p-2 rounded-xl hover:bg-primary-50 text-gray-600 hover:text-primary-600 transition-colors"
            aria-label="Menu"
          >
            <Menu className="h-6 w-6" />
          </button>
          {menuOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                aria-hidden
                onClick={() => setMenuOpen(false)}
              />
              <div className="absolute left-2 top-full mt-1 z-20 bg-white rounded-xl border border-[var(--border)] shadow-soft-lg py-1 min-w-[180px]">
                <button
                  type="button"
                  onClick={handleNewChat}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-sm text-gray-700 hover:bg-primary-50 rounded-lg mx-1"
                >
                  <RotateCcw className="h-4 w-4" />
                  New chat
                </button>
                <button
                  type="button"
                  onClick={handleStartFresh}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50 rounded-lg mx-1"
                >
                  <Trash2 className="h-4 w-4" />
                  Start fresh
                </button>
              </div>
            </>
          )}
          <button
            type="button"
            onClick={handleNewChat}
            className="p-2 rounded-xl hover:bg-primary-50 text-gray-600 hover:text-primary-600 transition-colors"
            title="New chat"
            aria-label="New chat"
          >
            <RotateCcw className="h-6 w-6" />
          </button>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary-500 text-white flex items-center justify-center">
            <Target className="w-4 h-4" strokeWidth={2.5} />
          </div>
          <h1 className="text-lg font-bold text-primary-600 tracking-tight hidden sm:block">
            AI Counsellor
          </h1>
        </div>
        <VoiceButton
          onRecordingComplete={handleVoiceResult}
          disabled={isLoading}
          className="p-2"
        />
      </header>

      {/* Ad slot — replace <AdSlot /> with your ad component when ready */}
      <div className="flex-shrink-0 px-2 py-1.5 bg-[var(--ad-slot-bg)]/50 border-b border-[var(--ad-slot-border)]">
        <div className="max-w-3xl mx-auto">
          <AdSlot variant="banner" />
        </div>
      </div>

      {/* Chat area */}
      <main className="flex-1 flex flex-col min-h-0">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSpeak={handleSpeak}
          collegesCache={collegesCache}
          setCollegesCache={setCollegesCache}
          messageSources={messageSources}
        />
      </main>

      {/* Suggested prompts — collapsible, show after first exchange, hide while loading */}
      {messages.length >= 2 && !isLoading && (
        <div className="flex-shrink-0 bg-white/80 border-t border-[var(--border)]">
          <button
            type="button"
            onClick={() => setSuggestionsOpen((o) => !o)}
            className="w-full flex items-center justify-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-primary-600 transition-colors"
          >
            Try asking
            {suggestionsOpen ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronUp className="h-3.5 w-3.5" />
            )}
          </button>
          {suggestionsOpen && (
            <div className="flex flex-wrap gap-2 justify-center max-w-3xl mx-auto px-3 pb-2">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => handleSuggestedPrompt(prompt)}
                  className="px-3 py-1.5 rounded-full text-sm bg-primary-50 text-primary-700 hover:bg-primary-100 border border-primary-200/80 transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Input bar */}
      <div className="flex-shrink-0 p-3 bg-white border-t border-[var(--border)] shadow-soft">
        <div className="flex gap-2 items-center max-w-3xl mx-auto">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Message likhein ya poochhein..."
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            className="flex-1 rounded-xl py-2.5 border-[var(--border)]"
          />
          {isLoading ? (
            <Button
              type="button"
              onClick={handleCancel}
              className="bg-red-100 text-red-700 hover:bg-red-200 border border-red-200 rounded-xl"
            >
              <Square className="h-4 w-4 mr-1" />
              Cancel
            </Button>
          ) : (
            <VoiceButton
              onRecordingComplete={handleVoiceResult}
              disabled={isLoading}
            />
          )}
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="rounded-xl px-4"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
