'use client'
import { useState, useRef, useCallback } from 'react'
import { Mic, Square } from 'lucide-react'

export default function VoiceButton({ onRecordingComplete, disabled = false, className = '' }) {
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  const startRecording = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        if (chunksRef.current.length > 0) {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
          onRecordingComplete(blob)
        }
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      setError('Microphone access denied or not supported.')
      console.error(err)
    }
  }, [onRecordingComplete])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }, [isRecording])

  if (error) {
    return (
      <span className="text-xs text-red-600 max-w-[120px]" title={error}>
        Mic unavailable
      </span>
    )
  }

  return (
    <button
      type="button"
      onClick={isRecording ? stopRecording : startRecording}
      disabled={disabled}
      className={`rounded-full p-2 transition-all focus:outline-none focus:ring-2 focus:ring-orange-400 ${
        isRecording
          ? 'bg-red-500 text-white animate-pulse'
          : 'bg-gray-100 text-gray-700 hover:bg-orange-100 hover:text-orange-600'
      } ${className}`}
      aria-label={isRecording ? 'Stop recording' : 'Start voice input'}
    >
      {isRecording ? (
        <Square className="h-5 w-5" fill="currentColor" />
      ) : (
        <Mic className="h-5 w-5" />
      )}
    </button>
  )
}
