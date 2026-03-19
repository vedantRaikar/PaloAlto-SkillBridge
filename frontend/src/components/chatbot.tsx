'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { chatbotApi, type ChatMessage, type ChatResponse } from '@/lib/api'
import { 
  Send, 
  Loader2, 
  Sparkles, 
  User,
  Lightbulb,
  MessageSquare,
  Zap,
  BookOpen,
  Award,
  Briefcase
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatbotProps {
  className?: string
}

const DEFAULT_SUGGESTIONS = [
  'What skills do I need for a backend developer role?',
  'How can I learn machine learning from scratch?',
  'What certifications are best for cloud computing?',
  'Compare Python vs JavaScript for web development',
  'What courses teach Docker and Kubernetes?',
]

export function Chatbot({ className = '' }: ChatbotProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS)
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e?: React.FormEvent, customMessage?: string) => {
    e?.preventDefault()
    const message = customMessage || input.trim()
    if (!message || isLoading) return

    const userMessage: ChatMessage = { role: 'user', content: message }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const history = messages.slice(-10)
      const response = await chatbotApi.chat(message, history)
      
      const assistantMessage: ChatMessage = { role: 'assistant', content: response.answer }
      setMessages(prev => [...prev, assistantMessage])
      setLastResponse(response)
      
      if (response.suggestions && response.suggestions.length > 0) {
        setSuggestions(response.suggestions)
      }
    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage: ChatMessage = { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error processing your request. Please try again.' 
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
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
    setLastResponse(null)
    setSuggestions(DEFAULT_SUGGESTIONS)
  }

  return (
    <Card className={cn('flex flex-col h-[600px]', className)}>
      <CardHeader className="pb-3 border-b">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            SkillBridge Assistant
          </CardTitle>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearChat}>
                Clear Chat
              </Button>
            )}
            <Badge variant="outline" className="text-xs">
              <Zap className="h-3 w-3 mr-1" />
              AI Powered
            </Badge>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          Ask questions about skills, careers, courses, and certifications
        </p>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                <MessageSquare className="h-8 w-8 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Welcome to SkillBridge Assistant</h3>
                <p className="text-sm text-muted-foreground max-w-md mt-1">
                  I can help you explore skills, learning paths, and career development. 
                  Try one of these questions or ask your own!
                </p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                {suggestions.slice(0, 4).map((suggestion, i) => (
                  <Button
                    key={i}
                    variant="outline"
                    size="sm"
                    className="text-sm"
                    onClick={() => handleSubmit(undefined, suggestion)}
                  >
                    <Lightbulb className="h-3 w-3 mr-1" />
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((message, i) => (
                <div
                  key={i}
                  className={cn(
                    'flex gap-3',
                    message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                  )}
                >
                  <div
                    className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                      message.role === 'user' 
                        ? 'bg-primary text-primary-foreground' 
                        : 'bg-secondary'
                    )}
                  >
                    {message.role === 'user' ? (
                      <User className="h-4 w-4" />
                    ) : (
                      <Sparkles className="h-4 w-4" />
                    )}
                  </div>
                  <div
                    className={cn(
                      'rounded-lg px-4 py-2 max-w-[80%]',
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    )}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div className="bg-muted rounded-lg px-4 py-2">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Thinking...
                    </div>
                  </div>
                </div>
              )}

              {lastResponse && !isLoading && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {lastResponse.entities_found.skills.length > 0 && (
                    <div className="flex items-center gap-2 text-xs">
                      <BookOpen className="h-3 w-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Skills:</span>
                      {lastResponse.entities_found.skills.slice(0, 5).map((skill, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {lastResponse.entities_found.occupations.length > 0 && (
                    <div className="flex items-center gap-2 text-xs">
                      <Briefcase className="h-3 w-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Roles:</span>
                      {lastResponse.entities_found.occupations.slice(0, 3).map((role, i) => (
                        <Badge key={i} variant="outline" className="text-xs">
                          {role}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {!isLoading && suggestions.length > 0 && (
                <div className="pt-2 border-t">
                  <p className="text-xs text-muted-foreground mb-2">Suggested follow-ups:</p>
                  <div className="flex flex-wrap gap-2">
                    {suggestions.slice(0, 3).map((suggestion, i) => (
                      <Button
                        key={i}
                        variant="ghost"
                        size="sm"
                        className="text-xs h-auto py-1"
                        onClick={() => handleSubmit(undefined, suggestion)}
                      >
                        {suggestion}
                      </Button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t bg-background">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about skills, courses, certifications..."
              className="flex-1 min-h-[44px] max-h-[120px] resize-none"
              disabled={isLoading}
            />
            <Button 
              type="submit" 
              size="icon" 
              className="h-[44px] w-[44px]"
              disabled={!input.trim() || isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </form>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
