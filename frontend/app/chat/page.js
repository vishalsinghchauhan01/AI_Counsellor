'use client'
import { useState, useEffect, useRef } from 'react'
import { useStore } from '@/lib/store'
import { getOnboardingMessage, sendChatMessage, speechToText, textToSpeech } from '@/lib/api'
import ChatWindow from '@/components/ChatWindow'
import VoiceButton from '@/components/VoiceButton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Menu, Send, RotateCcw, Square } from 'lucide-react'

const ERROR_MSG =
  'Abhi server se connect nahi ho pa raha. Please thodi der baad try karein.'

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
  } = useStore()

  const [input, setInput] = useState('')
  const [collegesCache, setCollegesCache] = useState({})
  const [initialLoad, setInitialLoad] = useState(true)
  const [menuOpen, setMenuOpen] = useState(false)
  const audioRef = useRef(null)
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

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isLoading) return

    setInput('')
    addMessage({ role: 'user', content: text })
    setLoading(true)
    addMessage({ role: 'assistant', content: '' })

    abortRef.current = new AbortController()

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
        { signal: abortRef.current.signal }
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

  const handleSpeak = async (text) => {
    try {
      const blob = await textToSpeech(text)
      const url = URL.createObjectURL(blob)
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.src = url
        audioRef.current.play()
      }
    } catch {
      // ignore TTS errors
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <audio ref={audioRef} className="hidden" />
      {/* Header */}
      <header className="flex-shrink-0 flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200 shadow-sm relative">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            className="p-2 rounded-lg hover:bg-gray-100"
            aria-label="Menu"
          >
            <Menu className="h-6 w-6 text-gray-600" />
          </button>
          {menuOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                aria-hidden
                onClick={() => setMenuOpen(false)}
              />
              <div className="absolute left-2 top-full mt-1 z-20 bg-white rounded-lg border border-gray-200 shadow-lg py-1 min-w-[140px]">
                <button
                  type="button"
                  onClick={handleNewChat}
                  className="w-full flex items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-orange-50"
                >
                  <RotateCcw className="h-4 w-4" />
                  New chat
                </button>
              </div>
            </>
          )}
          <button
            type="button"
            onClick={handleNewChat}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-600"
            title="New chat"
            aria-label="New chat"
          >
            <RotateCcw className="h-6 w-6" />
          </button>
        </div>
        <h1 className="text-lg font-bold text-orange-600">AI Counsellor 🎯</h1>
        <VoiceButton
          onRecordingComplete={handleVoiceResult}
          disabled={isLoading}
          className="p-2"
        />
      </header>

      {/* Chat area */}
      <main className="flex-1 flex flex-col min-h-0">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSpeak={handleSpeak}
          collegesCache={collegesCache}
          setCollegesCache={setCollegesCache}
        />
      </main>

      {/* Input bar */}
      <div className="flex-shrink-0 p-3 bg-white border-t border-gray-200">
        <div className="flex gap-2 items-center max-w-3xl mx-auto">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Message likhein..."
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            className="flex-1"
          />
          {isLoading ? (
            <Button
              type="button"
              onClick={handleCancel}
              className="bg-red-100 text-red-700 hover:bg-red-200 border border-red-200"
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
          <Button onClick={handleSend} disabled={!input.trim() || isLoading}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
