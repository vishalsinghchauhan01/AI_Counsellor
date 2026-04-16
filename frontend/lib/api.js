import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function sendChatMessage(message, history, userProfile, onChunk, onDone, options = {}) {
  const { signal, onSources } = options
  const response = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history: history.slice(-10).map((m) => ({ role: m.role, content: m.content })),
      user_profile: userProfile,
    }),
    signal,
  })

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const text = decoder.decode(value)
    const lines = text.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data === '[DONE]') {
          onDone()
          return
        }
        try {
          const parsed = JSON.parse(data)
          if (parsed.content) onChunk(parsed.content)
          if (parsed.sources && onSources) onSources(parsed.sources)
        } catch (e) {}
      }
    }
  }
}

export async function getOnboardingMessage() {
  const res = await axios.post(`${API_URL}/api/chat/onboarding`, {})
  return res.data.message
}

export async function speechToText(audioBlob) {
  const formData = new FormData()
  formData.append('audio', audioBlob, 'audio.webm')
  const res = await axios.post(`${API_URL}/api/voice/stt`, formData)
  return res.data.text
}

export async function textToSpeech(text) {
  // Use fetch instead of axios for true streaming — audio starts playing
  // as soon as the first bytes arrive instead of waiting for the full file
  const res = await fetch(`${API_URL}/api/voice/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!res.ok) throw new Error('TTS failed')
  return await res.blob()
}

export async function searchColleges(params) {
  const res = await axios.get(`${API_URL}/api/colleges/search`, { params })
  return res.data
}

export async function getAllColleges() {
  const res = await axios.get(`${API_URL}/api/colleges/all`)
  return res.data
}
