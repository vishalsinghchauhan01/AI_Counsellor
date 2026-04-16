import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const MAX_SAVED_CHATS = 5
const MAX_MESSAGES_PER_CHAT = 30

// Generate a short label from the first user message in a conversation
function chatLabel(messages) {
  const firstUser = messages.find((m) => m.role === 'user')
  if (!firstUser) return 'New Chat'
  const text = firstUser.content.slice(0, 50)
  return text.length < firstUser.content.length ? text + '…' : text
}

export const useStore = create(
  persist(
    (set, get) => ({
      // ── User profile ──────────────────────────────────────────
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

      // ── Current chat ──────────────────────────────────────────
      messages: [],        // current active conversation
      isLoading: false,
      sessionId: `session_${Date.now()}`,

      // ── Saved conversations ───────────────────────────────────
      // Each entry: { id, label, messages, createdAt }
      savedChats: [],
      activeChatId: null,  // id of the chat currently loaded (null = fresh chat)

      // ── Profile actions ───────────────────────────────────────
      updateUserProfile: (updates) => {
        set((state) => ({
          userProfile: { ...state.userProfile, ...updates },
        }))
        // Sync to backend (fire-and-forget, non-blocking)
        const profile = get().userProfile
        import('@/lib/api').then(({ saveUserProfile }) => {
          saveUserProfile({
            user_id: profile.user_id,
            current_class: profile.current_class || '',
            stream: profile.stream || '',
            career_interest: profile.career_interest || '',
            budget_per_year: profile.budget_per_year,
            category: profile.category || '',
            location: profile.location_preference || '',
            willing_to_relocate: profile.willing_to_relocate,
          })
        }).catch(() => {})
      },

      setIsOnboarded: (val) => set({ isOnboarded: val }),

      // Reset profile and all state — "Start Fresh" for a new user
      resetAll: () => set({
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
        messages: [],
        savedChats: [],
        activeChatId: null,
        sessionId: `session_${Date.now()}`,
        isLoading: false,
      }),

      // ── Message actions ───────────────────────────────────────
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

      setLastMessageSources: (sources) =>
        set((state) => {
          const messages = [...state.messages]
          if (messages.length > 0) {
            messages[messages.length - 1] = {
              ...messages[messages.length - 1],
              sources,
            }
          }
          return { messages }
        }),

      setLoading: (val) => set({ isLoading: val }),

      // ── Conversation management ───────────────────────────────

      // Save current chat to history, then clear for a new one
      clearMessages: () => {
        const { messages, savedChats, activeChatId, userProfile } = get()

        let updatedSaved = [...savedChats]

        // Only save if there's actual conversation (at least 1 user message)
        const hasUserMsg = messages.some((m) => m.role === 'user')
        if (hasUserMsg && messages.length >= 2) {
          const trimmedMessages = messages.slice(-MAX_MESSAGES_PER_CHAT)
          const label = chatLabel(trimmedMessages)

          if (activeChatId) {
            // Update existing saved chat
            updatedSaved = updatedSaved.map((c) =>
              c.id === activeChatId
                ? { ...c, messages: trimmedMessages, label }
                : c
            )
            // Sync to backend
            import('@/lib/api').then(({ saveConversation }) => {
              saveConversation(activeChatId, userProfile.user_id, label, trimmedMessages)
            }).catch(() => {})
          } else {
            // Save as new chat
            const chatId = `chat_${Date.now()}`
            const newChat = {
              id: chatId,
              label,
              messages: trimmedMessages,
              createdAt: Date.now(),
            }
            updatedSaved = [newChat, ...updatedSaved].slice(0, MAX_SAVED_CHATS)
            // Sync to backend
            import('@/lib/api').then(({ saveConversation }) => {
              saveConversation(chatId, userProfile.user_id, label, trimmedMessages)
            }).catch(() => {})
          }
        }

        set({
          messages: [],
          savedChats: updatedSaved,
          activeChatId: null,
          sessionId: `session_${Date.now()}`,
        })
      },

      // Load a saved chat into the active conversation
      loadChat: (chatId) => {
        const { savedChats } = get()
        const chat = savedChats.find((c) => c.id === chatId)
        if (!chat) return

        set({
          messages: [...chat.messages],
          activeChatId: chatId,
          sessionId: `session_${Date.now()}`,
        })
      },

      // Delete a saved chat
      deleteChat: (chatId) => {
        set((state) => ({
          savedChats: state.savedChats.filter((c) => c.id !== chatId),
          // If the deleted chat was active, clear current messages
          ...(state.activeChatId === chatId
            ? { messages: [], activeChatId: null }
            : {}),
        }))
        // Sync deletion to backend
        import('@/lib/api').then(({ deleteConversationApi }) => {
          deleteConversationApi(chatId)
        }).catch(() => {})
      },
    }),
    {
      name: 'ai-counsellor-storage',
      partialize: (state) => ({
        userProfile: state.userProfile,
        isOnboarded: state.isOnboarded,
        // Don't persist current messages — always start fresh on app open
        // Conversations are saved in savedChats when user clicks "New Chat"
        savedChats: state.savedChats.slice(0, MAX_SAVED_CHATS),
      }),
    }
  )
)
