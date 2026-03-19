'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { roadmapApi } from '@/lib/api'
import { useUserStore } from '@/stores/userStore'
import type { Role, Roadmap, WeekPlan } from '@/lib/types'
import { Clock, BookOpen, CheckCircle, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react'

const CATEGORY_COLORS: Record<string, string> = {
  programming: 'bg-blue-500',
  frontend: 'bg-purple-500',
  backend: 'bg-green-600',
  devops: 'bg-orange-600',
  cloud: 'bg-cyan-500',
  database: 'bg-yellow-500',
  ai: 'bg-pink-500',
  tools: 'bg-gray-500',
  unknown: 'bg-gray-400',
}

function RoadmapContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { userId, selectedRole, setSelectedRole } = useUserStore()
  
  const [roles, setRoles] = useState<Role[]>([])
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [expandedWeek, setExpandedWeek] = useState<number | null>(null)

  useEffect(() => {
    roadmapApi.roles().then((data) => {
      setRoles(data.roles || [])
    }).catch(console.error)

    const roleParam = searchParams.get('role')
    if (roleParam) {
      setSelectedRole(roleParam)
    }
  }, [searchParams, setSelectedRole])

  useEffect(() => {
    if (selectedRole && userId) {
      loadRoadmap()
    }
  }, [selectedRole, userId])

  const loadRoadmap = async () => {
    if (!selectedRole || !userId) return
    setIsLoading(true)
    try {
      const data = await roadmapApi.roadmap(userId, selectedRole)
      setRoadmap(data)
    } catch (error) {
      console.error('Failed to load roadmap:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getRoleTitle = (roleId: string) => {
    return roles.find((r) => r.id === roleId)?.title?.replace(/_/g, ' ') || roleId
  }

  const getCategoryColor = (category?: string) => {
    return CATEGORY_COLORS[category || 'unknown']
  }

  const scrollTimeline = (direction: 'left' | 'right') => {
    const container = document.getElementById('timeline')
    if (container) {
      const scrollAmount = 300
      container.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth'
      })
    }
  }

  if (!userId) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="container mx-auto px-4 max-w-4xl">
          <Card>
            <CardContent className="py-12 text-center">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <h2 className="text-xl font-semibold mb-2">Profile Required</h2>
              <p className="text-muted-foreground mb-4">Please build your profile first</p>
              <Button onClick={() => router.push('/profile')}>Build Profile</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        <h1 className="text-3xl font-bold mb-2">Learning Roadmap</h1>
        <p className="text-muted-foreground mb-6">
          Your personalized week-by-week learning path
        </p>

        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">Target Role</label>
          <select
            value={selectedRole || ''}
            onChange={(e) => setSelectedRole(e.target.value || null)}
            className="w-full max-w-md p-2 border rounded-md"
          >
            <option value="">Select a role...</option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.title?.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="text-center py-12">Generating your roadmap...</div>
        ) : roadmap ? (
          <>
            <Card className="mb-6">
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold capitalize">
                      {getRoleTitle(roadmap.target_role)}
                    </h2>
                    <p className="text-muted-foreground">
                      {roadmap.total_weeks} weeks to career readiness
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-blue-600">
                      {Math.round(roadmap.total_weeks * 7)} days
                    </div>
                    <p className="text-xs text-muted-foreground">Estimated duration</p>
                  </div>
                </div>
                {roadmap.fallback_used && (
                  <Badge variant="outline" className="mt-2">
                    Generated from knowledge graph
                  </Badge>
                )}
                {roadmap.ai_generated && (
                  <Badge variant="secondary" className="mt-2">
                    AI-enhanced roadmap
                  </Badge>
                )}
              </CardContent>
            </Card>

            <div className="relative mb-6">
              <Button
                variant="outline"
                size="icon"
                className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-white"
                onClick={() => scrollTimeline('left')}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              
              <div id="timeline" className="flex gap-4 overflow-x-auto pb-4 px-8">
                {roadmap.weeks.map((week: WeekPlan) => (
                  <div
                    key={week.week}
                    className={`flex-shrink-0 w-72 border rounded-lg p-4 cursor-pointer transition-all ${
                      expandedWeek === week.week
                        ? 'ring-2 ring-blue-500 shadow-lg'
                        : 'hover:shadow-md'
                    }`}
                    onClick={() => setExpandedWeek(expandedWeek === week.week ? null : week.week)}
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white text-sm font-bold">
                        {week.week}
                      </div>
                      <span className="text-sm text-muted-foreground">Week</span>
                    </div>
                    
                    <h3 className="font-semibold capitalize mb-2">
                      {week.skill.replace(/_/g, ' ')}
                    </h3>
                    
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`w-2 h-2 rounded-full ${getCategoryColor(week.skill_category)}`}></span>
                      <span className="text-xs text-muted-foreground capitalize">
                        {week.skill_category || 'General'}
                      </span>
                    </div>

                    {week.milestones.length > 0 && (
                      <div className="text-sm text-muted-foreground">
                        {week.milestones.length} milestones
                      </div>
                    )}

                    {expandedWeek === week.week && (
                      <div className="mt-4 pt-4 border-t space-y-4">
                        <div>
                          <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                            <BookOpen className="h-4 w-4" />
                            Recommended Resources
                          </h4>
                          {week.resources.length > 0 ? (
                            <div className="space-y-2">
                              {week.resources.map((course: any, idx: number) => (
                                <div key={idx} className="text-sm bg-gray-50 rounded p-2">
                                  <p className="font-medium truncate">{course.title || course}</p>
                                  {course.provider && (
                                    <p className="text-xs text-muted-foreground">{course.provider}</p>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground">No specific resources</p>
                          )}
                        </div>

                        <div>
                          <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                            <CheckCircle className="h-4 w-4" />
                            Milestones
                          </h4>
                          <ul className="space-y-1">
                            {week.milestones.map((milestone, idx) => (
                              <li key={idx} className="text-sm flex items-center gap-2">
                                <div className="w-4 h-4 rounded border border-gray-300"></div>
                                {milestone}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <Button
                variant="outline"
                size="icon"
                className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-white"
                onClick={() => scrollTimeline('right')}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex gap-4">
              <Button variant="outline" onClick={() => router.push('/analyze')}>
                Back to Analysis
              </Button>
              <Button onClick={() => router.push('/')}>
                Back to Dashboard
              </Button>
            </div>
          </>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <Clock className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <h2 className="text-xl font-semibold mb-2">No Roadmap Yet</h2>
              <p className="text-muted-foreground mb-4">
                Select a target role and build your profile to generate a learning roadmap
              </p>
              <Button onClick={() => router.push('/analyze')}>
                Go to Analysis
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

function RoadmapLoading() {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        <div className="animate-pulse">
          <div className="h-8 w-64 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 w-96 bg-gray-200 rounded mb-6"></div>
          <div className="h-12 w-full max-w-md bg-gray-200 rounded mb-6"></div>
          <div className="h-64 w-full bg-gray-200 rounded"></div>
        </div>
      </div>
    </div>
  )
}

export default function RoadmapPage() {
  return (
    <Suspense fallback={<RoadmapLoading />}>
      <RoadmapContent />
    </Suspense>
  )
}
