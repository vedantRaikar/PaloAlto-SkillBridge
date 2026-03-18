'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { roadmapApi, profileApi } from '@/lib/api'
import { useUserStore } from '@/stores/userStore'
import type { Role } from '@/lib/types'
import { Target, TrendingUp, Zap, ArrowRight } from 'lucide-react'

export default function Dashboard() {
  const [roles, setRoles] = useState<Role[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const { userId, name, skills, readinessScores, setUser, setReadinessScores } = useUserStore()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setIsLoading(true)
    try {
      const rolesData = await roadmapApi.roles()
      setRoles(rolesData.roles || [])
    } catch (error) {
      console.error('Failed to load roles:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (userId) {
      profileApi.readiness(userId).then((data) => {
        setReadinessScores(data.readiness_scores || {})
      }).catch(console.error)
    }
  }, [userId, setReadinessScores])

  const getScore = (roleId: string) => readinessScores[roleId] || 0

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-600'
    if (score >= 40) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 py-16">
        <div className="container mx-auto px-4">
          <div className="max-w-2xl">
            <h1 className="text-4xl font-bold text-white mb-4">
              Welcome to SkillBridge Navigator
            </h1>
            <p className="text-xl text-blue-100 mb-6">
              Bridge the gap between your current skills and your dream career
            </p>
            {!userId ? (
              <Link href="/profile">
                <Button size="lg" className="bg-white text-blue-600 hover:bg-blue-50">
                  Build Your Profile
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            ) : (
              <div className="bg-white/10 rounded-lg p-4 text-white">
                <p className="font-medium">Welcome back, {name}!</p>
                <p className="text-sm text-blue-100">You have {skills.length} skills mapped</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-12">
        <div className="grid gap-6 md:grid-cols-3 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Your Skills</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{skills.length}</div>
              <p className="text-xs text-muted-foreground">Skills mapped in your profile</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Career Paths</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{roles.length}</div>
              <p className="text-xs text-muted-foreground">Available career tracks</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Top Match</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {Object.keys(readinessScores).length > 0 ? (
                <>
                  <div className={`text-2xl font-bold ${getScoreColor(Math.max(...Object.values(readinessScores)))}`}>
                    {Math.max(...Object.values(readinessScores))}%
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {Object.entries(readinessScores).find(([_, v]) => v === Math.max(...Object.values(readinessScores)))?.[0]?.replace('_', ' ')}
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Build your profile to see matches</p>
              )}
            </CardContent>
          </Card>
        </div>

        <h2 className="text-2xl font-bold mb-6">Explore Career Paths</h2>
        {isLoading ? (
          <div className="text-center py-12">Loading career paths...</div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {roles.map((role) => {
              const score = getScore(role.id)
              return (
                <Card key={role.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <CardTitle className="capitalize">{role.title?.replace('_', ' ')}</CardTitle>
                    <CardDescription>Career Path</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {userId ? (
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Readiness</span>
                          <span className={`font-medium ${getScoreColor(score)}`}>{score}%</span>
                        </div>
                        <Progress value={score} className="h-2" />
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Build your profile to see your readiness score
                      </p>
                    )}
                  </CardContent>
                  <CardFooter className="gap-2">
                    {userId && score > 0 ? (
                      <Link href={`/roadmap?role=${role.id}`} className="flex-1">
                        <Button variant="outline" className="w-full">
                          View Roadmap
                        </Button>
                      </Link>
                    ) : (
                      <Link href="/profile" className="flex-1">
                        <Button variant="outline" className="w-full">
                          Build Profile
                        </Button>
                      </Link>
                    )}
                  </CardFooter>
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
