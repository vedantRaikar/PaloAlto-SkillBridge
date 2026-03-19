'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { learningApi } from '@/lib/api'
import type { Course } from '@/lib/types'
import { CourseCard, CourseCardSkeleton } from '@/components/course-card'
import { Search, BookOpen, Filter, Loader2, X, Check } from 'lucide-react'

const providers = ['all', 'udemy', 'coursera', 'youtube', 'edx']
const providerLabels: Record<string, string> = {
  all: 'All Platforms',
  udemy: 'Udemy',
  coursera: 'Coursera',
  youtube: 'YouTube',
  edx: 'edX',
}

const levels = [
  { value: '', label: 'All Levels' },
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
]

export default function CoursesPage() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedProvider, setSelectedProvider] = useState('all')
  const [selectedLevel, setSelectedLevel] = useState('')
  const [freeOnly, setFreeOnly] = useState(false)
  const [courses, setCourses] = useState<Course[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [providersList, setProvidersList] = useState<string[]>([])

  useEffect(() => {
    loadProviders()
  }, [])

  const loadProviders = async () => {
    try {
      const data = await learningApi.getProviders()
      setProvidersList(data.providers)
    } catch (error) {
      console.error('Failed to load providers:', error)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    setIsLoading(true)
    setHasSearched(true)
    try {
      const providers = selectedProvider === 'all' 
        ? ['all'] 
        : [selectedProvider]
      
      const data = await learningApi.searchCourses({
        skill: searchQuery,
        providers,
        max_results: 20,
        free_only: freeOnly,
        level: selectedLevel || undefined,
      })
      
      setCourses(data.courses)
    } catch (error) {
      console.error('Failed to search courses:', error)
      setCourses([])
    } finally {
      setIsLoading(false)
    }
  }

  const clearFilters = () => {
    setSelectedProvider('all')
    setSelectedLevel('')
    setFreeOnly(false)
    if (searchQuery) {
      handleSearch()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
              <BookOpen className="h-8 w-8 text-blue-500" />
              Course Discovery
            </h1>
            <p className="text-muted-foreground">
              Find the best courses to learn new skills from top platforms
            </p>
          </div>
        </div>

        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-lg">Search for Courses</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="What do you want to learn? (e.g., Python, React, AWS)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="pl-10 text-lg"
                />
              </div>
              <Button 
                onClick={handleSearch} 
                disabled={isLoading || !searchQuery.trim()}
                size="lg"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Search className="mr-2 h-4 w-4" />
                    Search
                  </>
                )}
              </Button>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Filters:</span>
              </div>

              <Tabs value={selectedProvider} onValueChange={setSelectedProvider}>
                <TabsList>
                  {providers.map((provider) => (
                    <TabsTrigger key={provider} value={provider}>
                      {providerLabels[provider]}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>

              <select
                value={selectedLevel}
                onChange={(e) => setSelectedLevel(e.target.value)}
                className="p-2 border rounded-md text-sm"
              >
                {levels.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>

              <Button
                variant={freeOnly ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFreeOnly(!freeOnly)}
                className="flex items-center gap-1"
              >
                {freeOnly ? <Check className="h-3 w-3" /> : null}
                Free Only
              </Button>

              {(selectedProvider !== 'all' || selectedLevel || freeOnly) && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="mr-1 h-3 w-3" />
                  Clear Filters
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {isLoading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <CourseCardSkeleton key={i} />
            ))}
          </div>
        ) : hasSearched ? (
          <>
            {courses.length > 0 ? (
              <>
                <div className="flex items-center justify-between mb-6">
                  <p className="text-muted-foreground">
                    Found <span className="font-semibold">{courses.length}</span> courses for "{searchQuery}"
                  </p>
                  <div className="flex gap-2">
                    {Object.entries(
                      courses.reduce((acc, c) => {
                        acc[c.provider] = (acc[c.provider] || 0) + 1
                        return acc
                      }, {} as Record<string, number>)
                    ).map(([provider, count]) => (
                      <Badge key={provider} variant="secondary">
                        {providerLabels[provider] || provider}: {count}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {courses.map((course) => (
                    <CourseCard key={course.id} course={course} />
                  ))}
                </div>
              </>
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <BookOpen className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <h2 className="text-xl font-semibold mb-2">No courses found</h2>
                  <p className="text-muted-foreground mb-4">
                    Try adjusting your search or filters
                  </p>
                  <Button variant="outline" onClick={clearFilters}>
                    Clear Filters
                  </Button>
                </CardContent>
              </Card>
            )}
          </>
        ) : (
          <div className="grid md:grid-cols-2 gap-8">
            <Card>
              <CardHeader>
                <CardTitle>Popular Searches</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {['Python', 'JavaScript', 'React', 'Machine Learning', 'AWS', 'Docker', 'SQL', 'TypeScript'].map((term) => (
                    <Button
                      key={term}
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setSearchQuery(term)
                        setTimeout(() => handleSearch(), 100)
                      }}
                    >
                      {term}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Quick Links</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button variant="outline" className="w-full justify-start" onClick={() => { setSearchQuery('cloud computing'); setTimeout(() => handleSearch(), 100) }}>
                  Cloud Computing Courses
                </Button>
                <Button variant="outline" className="w-full justify-start" onClick={() => { setSearchQuery('web development'); setTimeout(() => handleSearch(), 100) }}>
                  Web Development Courses
                </Button>
                <Button variant="outline" className="w-full justify-start" onClick={() => { setSearchQuery('data science'); setTimeout(() => handleSearch(), 100) }}>
                  Data Science Courses
                </Button>
                <Button variant="outline" className="w-full justify-start" onClick={() => router.push('/certifications')}>
                  <BookOpen className="mr-2 h-4 w-4" />
                  View Certifications
                </Button>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
