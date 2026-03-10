import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useStore = create(
  persist(
    (set, get) => ({
      // User profile
      userProfile: {
        user_id: `user_${Date.now()}`,
        current_class: null,
        stream: null,
        career_interest: null,
        budget_per_year: null,
        category: null,
        location_preference: null,
        willing_to_relocate: null,
      },
      isOnboarded: false,

      // Chat
      messages: [],
      isLoading: false,
      sessionId: `session_${Date.now()}`,

      // Actions
      updateUserProfile: (updates) =>
        set((state) => ({
          userProfile: { ...state.userProfile, ...updates },
        })),

      setIsOnboarded: (val) => set({ isOnboarded: val }),

      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      updateLastMessage: (content) =>
        set((state) => {
          const messages = [...state.messages]
          if (messages.length > 0) {
            messages[messages.length - 1] = {
              ...messages[messages.length - 1],
              content: messages[messages.length - 1].content + content,
            }
          }
          return { messages }
        }),

      setLoading: (val) => set({ isLoading: val }),

      clearMessages: () =>
        set({ messages: [], sessionId: `session_${Date.now()}` }),
    }),
    {
      name: 'uttarapath-storage',
      partialize: (state) => ({
        userProfile: state.userProfile,
        isOnboarded: state.isOnboarded,
        messages: state.messages.slice(-20), // save last 20 messages only
      }),
    }
  )
)
