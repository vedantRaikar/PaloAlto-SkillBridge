'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { jobsApi, roadmapApi } from '@/lib/api'
import { useUserStore } from '@/stores/userStore'
import { Loader2, CheckCircle, AlertCircle, ArrowRight, Briefcase } from 'lucide-react'
import type { Role } from '@/lib/types'

interface JobData {
  job_id: string
  data: {
    title: string
    company?: string
  }
  role_id?: string
  skills_extracted: number
  timestamp: string
}

interface RoleBatchResult {
  role_id: string
  role_name: string
  total_postings: number
  valid_postings: number
  skills_selected: number
  selected_skills: string[]
  readiness_hint: string
}

export default function JobsPage() {
  const router = useRouter()
  const { userId, setSelectedRole } = useUserStore()
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [recentJobs, setRecentJobs] = useState<JobData[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [customRoleName, setCustomRoleName] = useState('')
  const [batchPostings, setBatchPostings] = useState<string[]>(['', ''])
  const [batchLoading, setBatchLoading] = useState(false)
  const [batchResult, setBatchResult] = useState<RoleBatchResult | null>(null)

  useEffect(() => {
    loadRecentJobs()
    loadRoles()
  }, [])

  const loadRecentJobs = async () => {
    try {
      const response = await jobsApi.list(10)
      setRecentJobs(response.jobs || [])
    } catch (err) {
      console.error('Failed to load recent jobs:', err)
    }
  }

  const loadRoles = async () => {
    try {
      const response = await roadmapApi.roles()
      setRoles(response.roles || [])
    } catch (err) {
      console.error('Failed to load roles:', err)
    }
  }

  const updateBatchPosting = (index: number, value: string) => {
    setBatchPostings((prev) => prev.map((posting, i) => (i === index ? value : posting)))
  }

  const addBatchPosting = () => {
    setBatchPostings((prev) => [...prev, ''])
  }

  const removeBatchPosting = (index: number) => {
    setBatchPostings((prev) => {
      if (prev.length <= 2) return prev
      return prev.filter((_, i) => i !== index)
    })
  }

  const handleCreateRoleFromBatch = async () => {
    setError('')
    setSuccess('')
    setBatchResult(null)

    const roleName = customRoleName.trim()
    const descriptions = batchPostings.map((p) => p.trim()).filter(Boolean)

    if (!roleName) {
      setError('Please enter a custom role name.')
      return
    }

    if (descriptions.length < 2) {
      setError('Please paste at least 2 job descriptions for role aggregation.')
      return
    }

    if (descriptions.some((d) => d.length < 50)) {
      setError('Each job description should be at least 50 characters long.')
      return
    }

    setBatchLoading(true)
    try {
      const response = await jobsApi.ingestRoleBatch({
        role_name: roleName,
        job_descriptions: descriptions,
        min_frequency: 1,
      })

      setBatchResult(response)
      setSelectedRole(response.role_id)
      setSuccess(`Custom role '${response.role_name}' created with ${response.skills_selected} aggregated skills.`)

      await Promise.all([loadRoles(), loadRecentJobs()])
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.response?.data?.error || 'Failed to create role from job postings'
      setError(errorMsg)
    } finally {
      setBatchLoading(false)
    }
  }

  const handleSelectJob = async (job: JobData) => {
    if (job.role_id) {
      setSelectedRole(job.role_id)
      router.push(`/analyze?role=${job.role_id}`)
      return
    }
    router.push('/analyze')
  }

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">Create Role From Job Postings</h1>
            <p className="text-muted-foreground">
              Build one custom role from multiple similar synthetic job descriptions
            </p>
          </div>
          <Button variant="outline" onClick={() => router.push('/analyze')}>
            Skip to Analysis
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2 text-red-700">
            <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">Error</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start gap-2 text-green-700">
            <CheckCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">Success</p>
              <p className="text-sm">{success}</p>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Create Custom Role From Multiple Job Posts</CardTitle>
                <CardDescription>
                  Add a role name and paste multiple similar job descriptions to build one aggregated target role
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Custom Role Name</label>
                  <Input
                    placeholder="e.g. Cloud Platform Engineer"
                    value={customRoleName}
                    onChange={(e) => setCustomRoleName(e.target.value)}
                  />
                </div>

                <div className="space-y-3">
                  {batchPostings.map((posting, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium">Job Description #{index + 1}</label>
                        {batchPostings.length > 2 && (
                          <Button type="button" variant="outline" size="sm" onClick={() => removeBatchPosting(index)}>
                            Remove
                          </Button>
                        )}
                      </div>
                      <Textarea
                        value={posting}
                        onChange={(e) => updateBatchPosting(index, e.target.value)}
                        placeholder="Paste similar job description here..."
                        className="min-h-[140px] font-mono text-sm"
                      />
                    </div>
                  ))}
                </div>

                <div className="flex gap-3">
                  <Button type="button" variant="outline" onClick={addBatchPosting}>
                    Add Another Job Description
                  </Button>
                  <Button
                    type="button"
                    onClick={handleCreateRoleFromBatch}
                    disabled={batchLoading}
                    className="flex-1"
                  >
                    {batchLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Building Role...
                      </>
                    ) : (
                      <>
                        <Briefcase className="h-4 w-4 mr-2" />
                        Create Role From Batch
                      </>
                    )}
                  </Button>
                </div>

                {batchResult && (
                  <div className="pt-4 border-t space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold">{batchResult.role_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {batchResult.valid_postings}/{batchResult.total_postings} postings processed, {batchResult.skills_selected} skills selected
                        </p>
                      </div>
                      <Button onClick={() => router.push(`/analyze?role=${batchResult.role_id}`)}>
                        Analyze This Role
                        <ArrowRight className="h-4 w-4 ml-2" />
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {batchResult.selected_skills.slice(0, 18).map((skill) => (
                        <Badge key={skill} variant="secondary" className="capitalize">
                          {skill.replace(/_/g, ' ')}
                        </Badge>
                      ))}
                      {batchResult.selected_skills.length > 18 && (
                        <Badge variant="outline">+{batchResult.selected_skills.length - 18} more</Badge>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Recent Jobs</CardTitle>
                <CardDescription>
                  Recently analyzed job postings
                </CardDescription>
              </CardHeader>
              <CardContent>
                {recentJobs.length > 0 ? (
                  <div className="space-y-3">
                    {recentJobs.slice(0, 5).map((job) => (
                      <div
                        key={job.job_id}
                        className="p-3 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                        onClick={() => handleSelectJob(job)}
                      >
                        <p className="font-medium text-sm truncate">{job.data.title}</p>
                        {job.data.company && (
                          <p className="text-xs text-muted-foreground">{job.data.company}</p>
                        )}
                        <div className="flex items-center gap-2 mt-2">
                          <Badge variant="secondary" className="text-xs">
                            {job.skills_extracted} skills
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(job.timestamp)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No recent jobs. Add your first job posting!
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Available Roles</CardTitle>
                <CardDescription>
                  Roles discovered from job postings
                </CardDescription>
              </CardHeader>
              <CardContent>
                {roles.length > 0 ? (
                  <div className="space-y-2">
                    {roles.slice(0, 8).map((role) => (
                      <button
                        key={role.id}
                        onClick={() => {
                          setSelectedRole(role.id)
                          router.push(`/analyze?role=${role.id}`)
                        }}
                        className="w-full text-left p-2 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        <p className="text-sm font-medium capitalize">
                          {role.title?.replace(/_/g, ' ')}
                        </p>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Add job postings to discover roles
                  </p>
                )}
              </CardContent>
            </Card>

            {!userId && (
              <Card className="border-blue-200 bg-blue-50">
                <CardContent className="pt-6">
                  <div className="text-center">
                    <p className="text-sm text-blue-800 mb-3">
                      Build your profile to compare your skills with job requirements
                    </p>
                    <Button variant="outline" onClick={() => router.push('/profile')}>
                      Build Profile First
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
