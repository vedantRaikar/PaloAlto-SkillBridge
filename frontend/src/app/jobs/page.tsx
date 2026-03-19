'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { jobsApi, roadmapApi } from '@/lib/api'
import { useUserStore } from '@/stores/userStore'
import { Link2, FileText, Loader2, CheckCircle, AlertCircle, ArrowRight, Briefcase } from 'lucide-react'
import type { Role } from '@/lib/types'

interface JobData {
  job_id: string
  input_type: string
  source?: string
  data: {
    title: string
    company?: string
    description: string
    location?: string
    experience_level?: string
    employment_type?: string
    industries?: string[]
    skills?: string[]
  }
  extraction_result?: {
    success: boolean
    graph_updated: boolean
    role_id?: string
    skills_extracted: number
    method_used: string
    tiers_attempted: string[]
    fallback_triggered: boolean
  }
  graph_updated: boolean
  role_id?: string
  skills_extracted: number
  timestamp: string
}

export default function JobsPage() {
  const router = useRouter()
  const { userId, skills, setSelectedRole } = useUserStore()
  const [activeTab, setActiveTab] = useState('url')
  const [linkedinUrl, setLinkedinUrl] = useState('')
  const [jobText, setJobText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [currentJob, setCurrentJob] = useState<JobData | null>(null)
  const [recentJobs, setRecentJobs] = useState<JobData[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [isValidating, setIsValidating] = useState(false)

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

  const handleIngestJob = async () => {
    setError('')
    setSuccess('')
    setCurrentJob(null)

    const input = activeTab === 'url' ? linkedinUrl.trim() : jobText.trim()
    
    if (!input) {
      setError('Please provide a job URL or job description')
      return
    }

    if (activeTab === 'text' && input.length < 50) {
      setError('Job description is too short. Please provide more details.')
      return
    }

    setIsLoading(true)

    try {
      const requestData = activeTab === 'url' 
        ? { url: input }
        : { text: input }

      const response = await jobsApi.ingest(requestData)
      setCurrentJob(response)
      
      if (response.extraction_result?.success) {
        setSuccess(`Successfully extracted ${response.skills_extracted} skills from the job posting!`)
      } else {
        setError('Some extraction issues occurred. You can still use this job posting.')
      }

      if (response.role_id) {
        setSelectedRole(response.role_id)
      }

      await loadRecentJobs()
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.response?.data?.error || 'Failed to process job posting'
      
      if (activeTab === 'url' && (
        errorMsg.toLowerCase().includes('javascript') ||
        errorMsg.toLowerCase().includes('linkedin') ||
        errorMsg.toLowerCase().includes('scrape')
      )) {
        setError('LinkedIn URL detected. Please paste the job description directly in the text area below.')
        setActiveTab('text')
        if (linkedinUrl) setJobText(`Job URL: ${linkedinUrl}\n\n`)
      } else {
        setError(errorMsg)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleValidate = async () => {
    setIsValidating(true)
    setError('')
    
    try {
      const input = activeTab === 'url' ? linkedinUrl.trim() : jobText.trim()
      const requestData = activeTab === 'url' 
        ? { url: input }
        : { text: input }
      
      const response = await jobsApi.validate(requestData)
      
      if (!response.valid) {
        setError(response.error || response.issues?.join(', ') || 'Invalid input')
      }
    } catch (err: any) {
      console.error('Validation error:', err)
    } finally {
      setIsValidating(false)
    }
  }

  const handleAnalyzeWithJob = () => {
    if (currentJob?.role_id) {
      router.push(`/analyze?role=${currentJob.role_id}`)
    } else {
      router.push('/analyze')
    }
  }

  const handleSelectJob = async (job: JobData) => {
    setCurrentJob(job)
    if (job.role_id) {
      setSelectedRole(job.role_id)
    }
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
            <h1 className="text-3xl font-bold mb-2">Add Job Posting</h1>
            <p className="text-muted-foreground">
              Paste a LinkedIn job URL or enter job details to analyze required skills
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
                <CardTitle>Job Information</CardTitle>
                <CardDescription>
                  Enter a LinkedIn job URL or paste the job description
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList>
                    <TabsTrigger value="url">
                      <Link2 className="h-4 w-4 mr-2" />
                      LinkedIn URL
                    </TabsTrigger>
                    <TabsTrigger value="text">
                      <FileText className="h-4 w-4 mr-2" />
                      Paste Description
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="url" className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">LinkedIn Job URL</label>
                      <Input
                        placeholder="https://www.linkedin.com/jobs/view/..."
                        value={linkedinUrl}
                        onChange={(e) => setLinkedinUrl(e.target.value)}
                        className="font-mono text-sm"
                      />
                      <p className="text-xs text-muted-foreground">
                        Paste a LinkedIn job posting URL. Example: linkedin.com/jobs/view/123456789
                      </p>
                    </div>
                  </TabsContent>

                  <TabsContent value="text" className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Job Description</label>
                      <Textarea
                        placeholder="Paste the job description here...

Example format:
Senior Full Stack Developer at Tech Company
Location: San Francisco, CA

We are looking for a Senior Full Stack Developer with 5+ years of experience...

Requirements:
- 5+ years of JavaScript/TypeScript
- React or Vue.js experience
- Node.js backend development
- PostgreSQL and Redis
- AWS or GCP experience
- Docker and Kubernetes"
                        value={jobText}
                        onChange={(e) => setJobText(e.target.value)}
                        className="min-h-[300px] font-mono text-sm"
                      />
                      <p className="text-xs text-muted-foreground">
                        Paste the full job description including title, requirements, and responsibilities.
                      </p>
                    </div>
                  </TabsContent>
                </Tabs>

                <div className="flex gap-3 pt-4 border-t">
                  <Button 
                    onClick={handleIngestJob} 
                    disabled={isLoading || (!linkedinUrl.trim() && !jobText.trim())}
                    className="flex-1"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Briefcase className="h-4 w-4 mr-2" />
                        Analyze Job Posting
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>

            {currentJob && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>Extracted Job Details</span>
                    <Badge variant={currentJob.extraction_result?.success ? 'success' : 'secondary'}>
                      {currentJob.skills_extracted} skills extracted
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Job Title</label>
                      <p className="text-lg font-semibold">{currentJob.data.title}</p>
                    </div>
                    {currentJob.data.company && (
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Company</label>
                        <p className="text-lg">{currentJob.data.company}</p>
                      </div>
                    )}
                    {currentJob.data.location && (
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Location</label>
                        <p>{currentJob.data.location}</p>
                      </div>
                    )}
                    {currentJob.data.experience_level && (
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Experience Level</label>
                        <p>{currentJob.data.experience_level}</p>
                      </div>
                    )}
                  </div>

                  {currentJob.data.description && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Description Preview</label>
                      <p className="text-sm mt-1 p-3 bg-gray-50 rounded-md max-h-32 overflow-y-auto">
                        {currentJob.data.description.slice(0, 500)}
                        {currentJob.data.description.length > 500 && '...'}
                      </p>
                    </div>
                  )}

                  {currentJob.extraction_result && (
                    <div className="pt-4 border-t">
                      <label className="text-sm font-medium text-muted-foreground mb-2 block">Extraction Method</label>
                      <div className="flex flex-wrap gap-2 items-center">
                        <Badge variant="outline">
                          Method: {currentJob.extraction_result.method_used}
                        </Badge>
                        {currentJob.extraction_result.tiers_attempted && (
                          <span className="text-xs text-muted-foreground">
                            Tried: {currentJob.extraction_result.tiers_attempted.join(' → ')}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-3 pt-4">
                    <Button onClick={handleAnalyzeWithJob}>
                      Analyze Skills Gap
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                    <Button variant="outline" onClick={() => setCurrentJob(null)}>
                      Clear
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
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
