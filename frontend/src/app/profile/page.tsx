'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { profileApi } from '@/lib/api'
import { useUserStore } from '@/stores/userStore'
import { Github, Upload, Plus, X, CheckCircle, Loader2, AlertCircle } from 'lucide-react'

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

export default function ProfilePage() {
  const router = useRouter()
  const { setUser, setSkills, setGithubUsername, name, skills } = useUserStore()
  const [githubUsername, setGithubUsernameInput] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [manualSkill, setManualSkill] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleGitHubAnalyze = async () => {
    if (!githubUsername.trim()) return
    setIsAnalyzing(true)
    setError('')
    setSuccess('')
    try {
      const profile = await profileApi.github(githubUsername)
      setUser(profile)
      setSkills(profile.skills)
      setGithubUsername(profile.github?.username || null)
      setSuccess('GitHub profile analyzed successfully!')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to analyze GitHub profile')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    setIsUploading(true)
    setError('')
    setSuccess('')
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_id', `user_${Date.now()}`)
      
      const profile = await profileApi.resume(formData)
      setUser(profile)
      setSkills(profile.skills)
      setSuccess('Resume uploaded and skills extracted!')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to parse resume')
    } finally {
      setIsUploading(false)
    }
  }

  const handleAddManualSkill = () => {
    if (!manualSkill.trim()) return
    const skill = manualSkill.toLowerCase().replace(/\s+/g, '_')
    if (!skills.includes(skill)) {
      setSkills([...skills, skill])
    }
    setManualSkill('')
  }

  const handleRemoveSkill = (skill: string) => {
    setSkills(skills.filter((s) => s !== skill))
  }

  const getCategoryColor = (category?: string) => {
    return CATEGORY_COLORS[category || 'unknown']
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-4xl">
        <h1 className="text-3xl font-bold mb-2">Build Your Profile</h1>
        <p className="text-muted-foreground mb-8">
          Connect your skills from GitHub, upload your resume, or add them manually
        </p>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
            <AlertCircle className="h-5 w-5" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
            <CheckCircle className="h-5 w-5" />
            {success}
          </div>
        )}

        <Tabs defaultValue="github" className="space-y-6">
          <TabsList>
            <TabsTrigger value="github">
              <Github className="h-4 w-4 mr-2" />
              GitHub
            </TabsTrigger>
            <TabsTrigger value="resume">
              <Upload className="h-4 w-4 mr-2" />
              Resume
            </TabsTrigger>
            <TabsTrigger value="manual">
              <Plus className="h-4 w-4 mr-2" />
              Manual
            </TabsTrigger>
          </TabsList>

          <TabsContent value="github">
            <Card>
              <CardHeader>
                <CardTitle>Connect GitHub</CardTitle>
                <CardDescription>
                  Analyze your GitHub profile to extract programming languages and technologies
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter GitHub username"
                    value={githubUsername}
                    onChange={(e) => setGithubUsernameInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleGitHubAnalyze()}
                  />
                  <Button onClick={handleGitHubAnalyze} disabled={isAnalyzing || !githubUsername.trim()}>
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      'Analyze'
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="resume">
            <Card>
              <CardHeader>
                <CardTitle>Upload Resume</CardTitle>
                <CardDescription>
                  Upload your resume (PDF or DOCX) to automatically extract skills
                </CardDescription>
              </CardHeader>
              <CardContent>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleResumeUpload}
                  accept=".pdf,.docx,.doc"
                  className="hidden"
                />
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="h-12 w-12 mx-auto mb-4 text-blue-500 animate-spin" />
                      <p className="text-gray-600">Analyzing resume...</p>
                    </>
                  ) : (
                    <>
                      <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                      <p className="text-gray-600">Click to upload or drag and drop</p>
                      <p className="text-sm text-gray-400 mt-1">PDF or DOCX up to 10MB</p>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="manual">
            <Card>
              <CardHeader>
                <CardTitle>Add Skills Manually</CardTitle>
                <CardDescription>
                  Type skill names to add them to your profile
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g., Python, React, AWS"
                    value={manualSkill}
                    onChange={(e) => setManualSkill(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddManualSkill()}
                  />
                  <Button onClick={handleAddManualSkill} disabled={!manualSkill.trim()}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2 mt-4">
                  {['python', 'javascript', 'react', 'aws', 'docker', 'sql', 'git'].map((skill) => (
                    <button
                      key={skill}
                      onClick={() => {
                        if (!skills.includes(skill)) {
                          setSkills([...skills, skill])
                        }
                      }}
                      className="text-sm px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-full capitalize"
                    >
                      + {skill}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {skills.length > 0 && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Your Skills ({skills.length})</CardTitle>
              <CardDescription>These skills will be used for gap analysis</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {skills.map((skill) => (
                  <Badge
                    key={skill}
                    variant="secondary"
                    className="px-3 py-1 text-sm flex items-center gap-1"
                  >
                    {skill.replace(/_/g, ' ')}
                    <button
                      onClick={() => handleRemoveSkill(skill)}
                      className="ml-1 hover:text-red-500"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
              <div className="mt-6 flex gap-4">
                <Button onClick={() => router.push('/analyze')}>
                  Analyze Skills
                </Button>
                <Button variant="outline" onClick={() => router.push('/')}>
                  Back to Dashboard
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
