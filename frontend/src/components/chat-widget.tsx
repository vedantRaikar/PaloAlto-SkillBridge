'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { chatbotApi, type ChatMessage } from '@/lib/api'
import { useUserStore } from '@/stores/userStore'
import { 
  Send, 
  Loader2, 
  Sparkles, 
  User,
  MessageSquare,
  X,
  Minimize2,
  Maximize2
} from 'lucide-react'
import { cn } from '@/lib/utils'

const DEFAULT_SUGGESTIONS = [
  'What skills do I need for this role?',
  'How long to become job-ready?',
  'Best certifications for this path?',
  'Compare free vs paid courses',
]

interface ChatWidgetProps {
  className?: string
}

export function ChatWidget({ className = '' }: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { selectedRole } = useUserStore()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (isOpen) scrollToBottom()
  }, [messages, isOpen])

  const handleSubmit = async (e?: React.FormEvent, customMessage?: string) => {
    e?.preventDefault()
    const message = customMessage || input.trim()
    if (!message || isLoading) return

    const userMessage: ChatMessage = { role: 'user', content: message }
    const currentMessages = [...messages, userMessage]
    setMessages(currentMessages)
    setInput('')
    setIsLoading(true)

    try {
      const response = await chatbotApi.chat(message, currentMessages, selectedRole || undefined)
      
      const assistantMessage: ChatMessage = { role: 'assistant', content: response.answer }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage: ChatMessage = { 
        role: 'assistant', 
        content: 'Sorry, the assistant is currently unavailable. Please try again later.' 
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className={cn(
          'fixed bottom-6 right-6 w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-lg',
          'hover:scale-110 transition-transform flex items-center justify-center',
          'z-50',
          className
        )}
      >
        <MessageSquare className="h-6 w-6" />
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse" />
      </button>
    )
  }

  if (isMinimized) {
    return (
      <button
        onClick={() => setIsMinimized(false)}
        className={cn(
          'fixed bottom-6 right-6 w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-lg',
          'hover:scale-110 transition-transform flex items-center justify-center',
          'z-50',
          className
        )}
      >
        <Sparkles className="h-6 w-6" />
      </button>
    )
  }

  return (
    <Card 
      className={cn(
        'fixed bottom-6 right-6 w-96 max-h-[500px] flex flex-col shadow-2xl z-50',
        className
      )}
    >
      <div className="flex items-center justify-between p-4 border-b bg-primary text-primary-foreground rounded-t-lg">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          <span className="font-semibold">SkillBridge Assistant</span>
        </div>
        <div className="flex items-center gap-1">
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-8 w-8 text-primary-foreground hover:text-primary-foreground hover:bg-primary-foreground/20"
            onClick={() => setIsMinimized(true)}
          >
            <Minimize2 className="h-4 w-4" />
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-8 w-8 text-primary-foreground hover:text-primary-foreground hover:bg-primary-foreground/20"
            onClick={() => setIsOpen(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-80">
        {messages.length === 0 ? (
          <div className="text-center py-4 space-y-3">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
              <MessageSquare className="h-5 w-5 text-primary" />
            </div>
            <p className="text-sm text-muted-foreground">
              Ask me about skills, courses, or career paths for your selected role.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {DEFAULT_SUGGESTIONS.map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => handleSubmit(undefined, suggestion)}
                  className="text-xs px-3 py-1 rounded-full bg-muted hover:bg-primary/10 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, i) => (
              <div
                key={i}
                className={cn(
                  'flex gap-2',
                  message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                )}
              >
                <div
                  className={cn(
                    'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs',
                    message.role === 'user' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-secondary'
                  )}
                >
                  {message.role === 'user' ? <User className="h-3 w-3" /> : <Sparkles className="h-3 w-3" />}
                </div>
                <div
                  className={cn(
                    'rounded-lg px-3 py-2 text-sm max-w-[80%]',
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  )}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-2">
                <div className="w-6 h-6 rounded-full bg-secondary flex items-center justify-center">
                  <Sparkles className="h-3 w-3" />
                </div>
                <div className="bg-muted rounded-lg px-3 py-2">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Thinking...
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {messages.length > 0 && (
        <div className="px-4 pb-2">
          <div className="flex gap-2 overflow-x-auto pb-2">
            {DEFAULT_SUGGESTIONS.map((suggestion, i) => (
              <button
                key={i}
                onClick={() => handleSubmit(undefined, suggestion)}
                className="text-xs px-2 py-1 rounded-full bg-muted hover:bg-primary/10 whitespace-nowrap transition-colors"
                disabled={isLoading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="p-3 border-t flex gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question..."
          className="flex-1 min-h-[40px] max-h-[80px] resize-none text-sm"
          disabled={isLoading}
        />
        <Button 
          type="submit" 
          size="icon" 
          className="h-[40px] w-[40px]"
          disabled={!input.trim() || isLoading}
          onClick={() => handleSubmit()}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </Card>
  )
}
