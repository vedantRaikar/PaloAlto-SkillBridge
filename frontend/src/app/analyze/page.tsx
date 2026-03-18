'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { roadmapApi } from '@/lib/api'
import { useUserStore } from '@/stores/userStore'
import type { Role, GapAnalysis, SkillGap } from '@/lib/types'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import { Target, CheckCircle, AlertCircle, ArrowRight } from 'lucide-react'

const COLORS = ['#22c55e', '#f97316', '#3b82f6', '#8b5cf6', '#ec4899']

export default function AnalyzePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { userId, skills, selectedRole, setSelectedRole } = useUserStore()
  
  const [roles, setRoles] = useState<Role[]>([])
  const [gapAnalysis, setGapAnalysis] = useState<GapAnalysis | null>(null)
  const [isLoading, setIsLoading] = useState(false)

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

  const getRoleTitle = (roleId: string) => {
    return roles.find((r) => r.id === roleId)?.title?.replace(/_/g, ' ') || roleId
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
      <div className="container mx-auto px-4 max-w-6xl">
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
              <div className={`text-2xl font-bold ${gapAnalysis?.readiness_score >= 70 ? 'text-green-600' : gapAnalysis?.readiness_score >= 40 ? 'text-yellow-600' : 'text-red-600'}`}>
                {gapAnalysis?.readiness_score || 0}%
              </div>
              <Progress value={gapAnalysis?.readiness_score || 0} className="mt-2 h-2" />
            </CardContent>
          </Card>
        </div>

        {isLoading ? (
          <div className="text-center py-12">Analyzing skills...</div>
        ) : gapAnalysis ? (
          <div className="grid md:grid-cols-2 gap-6">
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

            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Gap Overview</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
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
                <div className="text-center mt-4">
                  <Button onClick={() => router.push(`/roadmap?role=${selectedRole}`)}>
                    Generate Learning Roadmap
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>

            {gapAnalysis.gap_analysis.missing_skills.length > 0 && (
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle>Recommended Courses for Gap Skills</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {gapAnalysis.gap_analysis.missing_skills.slice(0, 6).map((skill) => {
                      const courses = gapAnalysis.gap_analysis.courses_for_gaps[skill] || []
                      return (
                        <div key={skill} className="border rounded-lg p-4">
                          <h4 className="font-medium capitalize mb-2">{skill.replace(/_/g, ' ')}</h4>
                          {courses.length > 0 ? (
                            <div className="space-y-2">
                              {courses.slice(0, 2).map((course: any) => (
                                <div key={course.id} className="text-sm">
                                  <p className="font-medium truncate">{course.title}</p>
                                  <p className="text-muted-foreground text-xs">{course.provider}</p>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground">No courses available</p>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
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
