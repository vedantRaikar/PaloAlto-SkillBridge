'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { roadmapApi, learningApi, profileApi, type UserKnowledgeGraph } from '@/lib/api'
import { useUserStore } from '@/stores/userStore'
import { CourseCard, CourseCardSkeleton } from '@/components/course-card'
import { CertificationCard, CertificationCardSkeleton } from '@/components/certification-card'
import { ChatWidget } from '@/components/chat-widget'
import { FastTrackPath } from '@/components/fast-track-path'
import type { Role, GapAnalysis } from '@/lib/types'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import { Target, CheckCircle, AlertCircle, ArrowRight, BookOpen, Loader2, Zap } from 'lucide-react'

const COLORS = ['#22c55e', '#f97316', '#3b82f6', '#8b5cf6', '#ec4899']

interface LearningResources {
  courses: any[]
  certifications: any[]
  loading: boolean
}

function AnalyzePageLoader() {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="text-center py-12 flex items-center justify-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading...</span>
        </div>
      </div>
    </div>
  )
}

function AnalyzePageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { userId, skills, selectedRole, setSelectedRole } = useUserStore()
  
  const [roles, setRoles] = useState<Role[]>([])
  const [gapAnalysis, setGapAnalysis] = useState<GapAnalysis | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [graphLoading, setGraphLoading] = useState(false)
  const [userGraph, setUserGraph] = useState<UserKnowledgeGraph | null>(null)
  const [graphError, setGraphError] = useState('')
  const [learningResources, setLearningResources] = useState<LearningResources>({
    courses: [],
    certifications: [],
    loading: false,
  })

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
      loadGapAnalysis()
    }
  }, [selectedRole, userId])

  useEffect(() => {
    if (gapAnalysis?.gap_analysis.missing_skills.length) {
      loadLearningResources(gapAnalysis.gap_analysis.missing_skills)
    }
  }, [gapAnalysis])

  const loadGapAnalysis = async () => {
    if (!selectedRole || !userId) return
    setIsLoading(true)
    try {
      const analysis = await roadmapApi.gapAnalysis(userId, selectedRole)
      setGapAnalysis(analysis)
    } catch (error) {
      console.error('Failed to load gap analysis:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadLearningResources = async (missingSkills: string[]) => {
    setLearningResources(prev => ({ ...prev, loading: true }))
    try {
      const resources = await learningApi.getResourcesForGap(missingSkills, skills)
      
      const allCourses: any[] = []
      const allCerts: any[] = []
      
      Object.values(resources.resources || {}).forEach((resource: any) => {
        if (resource.courses) {
          allCourses.push(...resource.courses)
        }
        if (resource.certifications) {
          allCerts.push(...resource.certifications)
        }
      })
      
      const uniqueCourses = allCourses.filter((c, i, arr) => 
        arr.findIndex(x => x.id === c.id) === i
      )
      
      const uniqueCerts = allCerts.filter((c, i, arr) => 
        arr.findIndex(x => x.id === c.id) === i
      ).slice(0, 6)
      
      setLearningResources({
        courses: uniqueCourses,
        certifications: uniqueCerts,
        loading: false,
      })
    } catch (error) {
      console.error('Failed to load learning resources:', error)
      setLearningResources(prev => ({ ...prev, loading: false }))
    }
  }

  const loadUserGraphPreview = async () => {
    if (!userId) return
    setGraphLoading(true)
    setGraphError('')
    try {
      const graph = await profileApi.graph(userId, 2)
      setUserGraph(graph)
    } catch (error: any) {
      const message = error?.response?.data?.detail || 'Failed to load your knowledge graph preview.'
      setGraphError(message)
    } finally {
      setGraphLoading(false)
    }
  }

  const chartData = gapAnalysis
    ? [
        { name: 'Matched', value: gapAnalysis.gap_analysis.matched_skills.length, color: '#22c55e' },
        { name: 'Gap', value: gapAnalysis.gap_analysis.missing_skills.length, color: '#f97316' },
      ]
    : []

  if (!userId) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="container mx-auto px-4 max-w-4xl">
          <Card>
            <CardContent className="py-12 text-center">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <h2 className="text-xl font-semibold mb-2">Profile Required</h2>
              <p className="text-muted-foreground mb-4">Please build your profile first to analyze your skills</p>
              <Button onClick={() => router.push('/profile')}>Build Profile</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-7xl">
        <h1 className="text-3xl font-bold mb-2">Skill Gap Analysis</h1>
        <p className="text-muted-foreground mb-8">
          Identify the skills you need to acquire for your target career
        </p>

        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Target Role</CardTitle>
            </CardHeader>
            <CardContent>
              <select
                value={selectedRole || ''}
                onChange={(e) => setSelectedRole(e.target.value || null)}
                className="w-full p-2 border rounded-md"
              >
                <option value="">Select a role...</option>
                {roles.map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.title?.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Your Skills</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{skills.length}</div>
              <p className="text-xs text-muted-foreground">Skills in your profile</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Readiness Score</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${
                (gapAnalysis?.readiness_score ?? 0) >= 70 
                  ? 'text-green-600' 
                  : (gapAnalysis?.readiness_score ?? 0) >= 40 
                    ? 'text-yellow-600' 
                    : 'text-red-600'
              }`}>
                {gapAnalysis?.readiness_score ?? 0}%
              </div>
              <Progress value={gapAnalysis?.readiness_score ?? 0} className="mt-2 h-2" />
            </CardContent>
          </Card>
        </div>

        <Card className="mb-8">
          <CardHeader>
            <CardTitle>My Knowledge Graph</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-3 items-center">
              <Button onClick={loadUserGraphPreview} disabled={graphLoading}>
                {graphLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading Graph...
                  </>
                ) : (
                  'View My Graph Preview'
                )}
              </Button>
              {userGraph && (
                <Button variant="outline" onClick={() => router.push('/graph')}>
                  Open Full Graph View
                </Button>
              )}
            </div>

            {graphError && (
              <p className="text-sm text-red-600">{graphError}</p>
            )}

            {userGraph && (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary">Nodes: {userGraph.node_count}</Badge>
                  <Badge variant="secondary">Edges: {userGraph.edge_count}</Badge>
                  <Badge variant="secondary">Depth: {userGraph.depth}</Badge>
                </div>

                <div>
                  <p className="text-sm font-medium mb-2">Connected Skills (sample)</p>
                  <div className="flex flex-wrap gap-2">
                    {userGraph.nodes
                      .filter((n) => n.type === 'skill')
                      .slice(0, 12)
                      .map((n) => (
                        <Badge key={n.id} variant="outline" className="capitalize">
                          {(n.title || n.id).replace(/_/g, ' ')}
                        </Badge>
                      ))}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {gapAnalysis && gapAnalysis.readiness_score < 100 && (
          <FastTrackPath className="mb-8" />
        )}

        {isLoading ? (
          <div className="text-center py-12 flex items-center justify-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Analyzing skills...</span>
          </div>
        ) : gapAnalysis ? (
          <>
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    Skills You Have ({gapAnalysis.gap_analysis.matched_skills.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {gapAnalysis.gap_analysis.matched_skills.length > 0 ? (
                      gapAnalysis.gap_analysis.matched_skills.map((skill) => (
                        <Badge key={skill} variant="success" className="capitalize">
                          {skill.replace(/_/g, ' ')}
                        </Badge>
                      ))
                    ) : (
                      <p className="text-muted-foreground">No matching skills found</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-orange-500" />
                    Skills You Need ({gapAnalysis.gap_analysis.missing_skills.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {gapAnalysis.gap_analysis.missing_skills.length > 0 ? (
                      gapAnalysis.gap_analysis.missing_skills.map((skill) => (
                        <Badge key={skill} variant="warning" className="capitalize">
                          {skill.replace(/_/g, ' ')}
                        </Badge>
                      ))
                    ) : (
                      <p className="text-green-600 font-medium">You're all set! No gaps found.</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid md:grid-cols-3 gap-6 mb-8">
              <Card className="md:col-span-1">
                <CardHeader>
                  <CardTitle>Gap Overview</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={chartData}
                          cx="50%"
                          cy="50%"
                          innerRadius={40}
                          outerRadius={60}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle>Recommended Certifications</CardTitle>
                </CardHeader>
                <CardContent>
                  {learningResources.loading ? (
                    <div className="grid md:grid-cols-2 gap-4">
                      <CertificationCardSkeleton />
                      <CertificationCardSkeleton />
                    </div>
                  ) : learningResources.certifications.length > 0 ? (
                    <div className="grid md:grid-cols-2 gap-4">
                      {learningResources.certifications.map((cert) => (
                        <CertificationCard key={cert.id} certification={cert} compact />
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-4">
                      No certifications found for your skill gaps
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>

            {gapAnalysis.gap_analysis.missing_skills.length > 0 && (
              <Card className="mb-8">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-blue-500" />
                    Recommended Courses for Gap Skills
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {learningResources.loading ? (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                      {[1, 2, 3, 4].map((i) => (
                        <CourseCardSkeleton key={i} />
                      ))}
                    </div>
                  ) : learningResources.courses.length > 0 ? (
                    <div className="max-h-[70vh] overflow-y-auto pr-2">
                      <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                        {learningResources.courses.map((course) => (
                          <CourseCard key={course.id} course={course} compact />
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-8">
                      No courses available for your skill gaps yet. 
                      <br />
                      <Button variant="link" onClick={() => router.push('/courses')}>
                        Search for courses manually
                      </Button>
                    </p>
                  )}
                  
                  <div className="mt-6 pt-6 border-t flex gap-4">
                    <Button onClick={() => router.push(`/roadmap?role=${selectedRole}`)}>
                      Generate Learning Roadmap
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                    <Button variant="outline" onClick={() => router.push('/courses')}>
                      <BookOpen className="mr-2 h-4 w-4" />
                      Browse All Courses
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <Target className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <h2 className="text-xl font-semibold mb-2">Select a Target Role</h2>
              <p className="text-muted-foreground">Choose a career path above to analyze your skill gaps</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<AnalyzePageLoader />}>
      <AnalyzePageContent />
      <ChatWidget />
    </Suspense>
  )
}
