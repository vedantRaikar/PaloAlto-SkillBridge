'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { roadmapApi, type FastTrackPath } from '@/lib/api'
import { useUserStore } from '@/stores/userStore'
import { 
  Zap, 
  Clock, 
  Target, 
  TrendingUp, 
  Play, 
  BookOpen, 
  Award,
  CheckCircle,
  ChevronRight,
  Loader2
} from 'lucide-react'

interface FastTrackPathProps {
  className?: string
}

export function FastTrackPath({ className = '' }: FastTrackPathProps) {
  const { userId, selectedRole } = useUserStore()
  const [fastTrack, setFastTrack] = useState<FastTrackPath | null>(null)
  const [completePath, setCompletePath] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [showComparison, setShowComparison] = useState(false)

  const loadFastTrack = async (maxSkills: number = 5) => {
    if (!userId || !selectedRole) return
    
    setLoading(true)
    try {
      const [ft, complete] = await Promise.all([
        roadmapApi.getFastTrack(userId, selectedRole, maxSkills),
        roadmapApi.getLearningPath(userId, selectedRole)
      ])
      setFastTrack(ft)
      setCompletePath(complete)
      setShowComparison(true)
    } catch (error) {
      console.error('Failed to load fast track:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!userId || !selectedRole) {
    return null
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-yellow-500" />
          Fast Track to Job Readiness
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!fastTrack ? (
          <div className="text-center py-8 space-y-4">
            <div className="w-16 h-16 rounded-full bg-yellow-100 flex items-center justify-center mx-auto">
              <Zap className="h-8 w-8 text-yellow-500" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">Ready for the Fast Track?</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Get the quickest path to job readiness with prioritized skills and a week-by-week plan.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              <Button onClick={() => loadFastTrack(3)} disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Zap className="h-4 w-4 mr-2" />}
                3 Skills (Super Fast)
              </Button>
              <Button onClick={() => loadFastTrack(5)} disabled={loading} variant="default">
                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Zap className="h-4 w-4 mr-2" />}
                5 Skills (Recommended)
              </Button>
              <Button onClick={() => loadFastTrack(7)} disabled={loading} variant="outline">
                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Zap className="h-4 w-4 mr-2" />}
                7 Skills (More Complete)
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <Target className="h-6 w-6 mx-auto text-green-600 mb-2" />
                <div className="text-2xl font-bold text-green-600">{fastTrack.projected_readiness}%</div>
                <div className="text-xs text-muted-foreground">Job Readiness</div>
              </div>
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <Clock className="h-6 w-6 mx-auto text-blue-600 mb-2" />
                <div className="text-2xl font-bold text-blue-600">{fastTrack.total_weeks}w</div>
                <div className="text-xs text-muted-foreground">Time to Job Ready</div>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <TrendingUp className="h-6 w-6 mx-auto text-yellow-600 mb-2" />
                <div className="text-2xl font-bold text-yellow-600">{fastTrack.total_hours}h</div>
                <div className="text-xs text-muted-foreground">Total Study Time</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <BookOpen className="h-6 w-6 mx-auto text-purple-600 mb-2" />
                <div className="text-2xl font-bold text-purple-600">{fastTrack.fast_track_skills.length}</div>
                <div className="text-xs text-muted-foreground">Skills to Learn</div>
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-3 flex items-center gap-2">
                <Play className="h-4 w-4 text-green-500" />
                Your Skills ({fastTrack.user_skills.length})
              </h4>
              <div className="flex flex-wrap gap-2">
                {fastTrack.user_skills.map((skill) => (
                  <Badge key={skill} variant="secondary" className="capitalize">
                    <CheckCircle className="h-3 w-3 mr-1 text-green-500" />
                    {skill.replace(/_/g, ' ')}
                  </Badge>
                ))}
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-3 flex items-center gap-2">
                <Zap className="h-4 w-4 text-yellow-500" />
                Priority Skills to Learn
              </h4>
              <div className="space-y-2">
                {fastTrack.skill_details.map((skill, index) => (
                  <div key={skill.skill} className="flex items-center gap-3 p-3 border rounded-lg">
                    <div className="w-8 h-8 rounded-full bg-yellow-100 flex items-center justify-center text-yellow-600 font-bold">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium capitalize">{skill.skill.replace(/_/g, ' ')}</span>
                        <Badge variant="outline" className="text-xs">
                          Impact: {skill.impact_score}/10
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground mt-1">
                        <span>{skill.duration_hours}h</span>
                        {skill.courses[0] && (
                          <span className="flex items-center gap-1">
                            <BookOpen className="h-3 w-3" />
                            {skill.courses[0].title}
                          </span>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-3 flex items-center gap-2">
                <Clock className="h-4 w-4 text-blue-500" />
                Week-by-Week Study Plan
              </h4>
              <div className="space-y-2">
                {fastTrack.study_plan.map((week, index) => (
                  <div key={index} className="flex items-center gap-3 p-2 rounded-lg bg-slate-50">
                    <Badge variant="outline" className="w-16 justify-center">
                      Week {week.week}
                    </Badge>
                    <div className="flex-1">
                      <span className="text-sm">{week.topic}</span>
                    </div>
                    <Badge variant="secondary">{week.hours}h</Badge>
                  </div>
                ))}
              </div>
            </div>

            {showComparison && completePath && (
              <div className="border-t pt-4">
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-purple-500" />
                  Path Comparison
                </h4>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="p-4 border rounded-lg bg-yellow-50">
                    <div className="flex items-center gap-2 mb-2">
                      <Zap className="h-4 w-4 text-yellow-500" />
                      <span className="font-semibold">Fast Track</span>
                    </div>
                    <div className="text-2xl font-bold text-yellow-600">{fastTrack.total_weeks} weeks</div>
                    <div className="text-sm text-muted-foreground">{fastTrack.fast_track_skills.length} essential skills</div>
                    <div className="mt-2 h-2 w-full bg-yellow-200 rounded-full overflow-hidden">
                      <div className="h-full bg-yellow-500 rounded-full" style={{ width: '100%' }} />
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">{fastTrack.projected_readiness}% job ready</div>
                  </div>
                  <div className="p-4 border rounded-lg bg-purple-50">
                    <div className="flex items-center gap-2 mb-2">
                      <BookOpen className="h-4 w-4 text-purple-500" />
                      <span className="font-semibold">Complete Path</span>
                    </div>
                    <div className="text-2xl font-bold text-purple-600">{completePath.estimated_weeks} weeks</div>
                    <div className="text-sm text-muted-foreground">{completePath.total_skills_to_learn} all skills</div>
                    <div className="mt-2 h-2 w-full bg-purple-200 rounded-full overflow-hidden">
                      <div className="h-full bg-purple-500 rounded-full" style={{ width: '100%' }} />
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">100% job ready</div>
                  </div>
                </div>
                <div className="mt-3 text-center text-sm">
                  <span className="text-green-600 font-semibold">
                    Save {completePath.estimated_weeks - fastTrack.total_weeks} weeks with Fast Track!
                  </span>
                </div>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <Button variant="outline" onClick={() => { setFastTrack(null); setShowComparison(false); }}>
                Choose Different Path
              </Button>
              <Button onClick={() => loadFastTrack(5)}>
                Refresh
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
