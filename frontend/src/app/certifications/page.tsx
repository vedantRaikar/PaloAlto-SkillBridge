'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { learningApi } from '@/lib/api'
import type { Certification } from '@/lib/types'
import { CertificationCard, CertificationCardSkeleton } from '@/components/certification-card'
import { Search, Award, Filter, Loader2, X, ExternalLink } from 'lucide-react'

const providers = ['all', 'aws', 'gcp', 'azure', 'comptia', 'hashicorp']
const providerLabels: Record<string, string> = {
  all: 'All Providers',
  aws: 'AWS',
  gcp: 'Google Cloud',
  azure: 'Microsoft Azure',
  comptia: 'CompTIA',
  hashicorp: 'HashiCorp',
}

const levels = [
  { value: '', label: 'All Levels' },
  { value: 'fundamentals', label: 'Fundamentals' },
  { value: 'associate', label: 'Associate' },
  { value: 'professional', label: 'Professional' },
  { value: 'expert', label: 'Expert' },
]

interface CertProvider {
  id: string
  name: string
  url: string
  certifications_count: number
  popular_certs: string[]
}

export default function CertificationsPage() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedProvider, setSelectedProvider] = useState('all')
  const [selectedLevel, setSelectedLevel] = useState('')
  const [certifications, setCertifications] = useState<Certification[]>([])
  const [providersList, setProvidersList] = useState<CertProvider[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  useEffect(() => {
    loadCertifications()
    loadProviders()
  }, [])

  const loadCertifications = async () => {
    setIsLoading(true)
    try {
      const data = await learningApi.searchCertifications({
        max_results: 50,
      })
      setCertifications(data.certifications)
      setHasSearched(true)
    } catch (error) {
      console.error('Failed to load certifications:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadProviders = async () => {
    try {
      const data = await learningApi.getCertProviders()
      setProvidersList(data.providers)
    } catch (error) {
      console.error('Failed to load providers:', error)
    }
  }

  const handleSearch = async () => {
    setIsLoading(true)
    setHasSearched(true)
    try {
      const data = await learningApi.searchCertifications({
        skill: searchQuery || undefined,
        provider: selectedProvider === 'all' ? undefined : selectedProvider,
        level: selectedLevel || undefined,
        max_results: 50,
      })
      setCertifications(data.certifications)
    } catch (error) {
      console.error('Failed to search certifications:', error)
      setCertifications([])
    } finally {
      setIsLoading(false)
    }
  }

  const clearFilters = () => {
    setSearchQuery('')
    setSelectedProvider('all')
    setSelectedLevel('')
    loadCertifications()
  }

  const filteredCerts = certifications.filter((cert) => {
    if (selectedProvider !== 'all' && cert.provider !== selectedProvider) return false
    if (selectedLevel && cert.level !== selectedLevel) return false
    return true
  })

  const certsByProvider = filteredCerts.reduce((acc, cert) => {
    acc[cert.provider] = acc[cert.provider] || []
    acc[cert.provider].push(cert)
    return acc
  }, {} as Record<string, Certification[]>)

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
              <Award className="h-8 w-8 text-yellow-500" />
              Certifications
            </h1>
            <p className="text-muted-foreground">
              Industry-recognized certifications to boost your career
            </p>
          </div>
        </div>

        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-lg">Find Certifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by skill (e.g., AWS, Security, Cloud)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Button onClick={handleSearch} disabled={isLoading}>
                {isLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                Search
              </Button>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Filter by:</span>
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

              {(selectedProvider !== 'all' || selectedLevel || searchQuery) && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="mr-1 h-3 w-3" />
                  Clear
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {isLoading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <CertificationCardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <>
            {filteredCerts.length > 0 ? (
              <>
                <div className="flex items-center justify-between mb-6">
                  <p className="text-muted-foreground">
                    Showing <span className="font-semibold">{filteredCerts.length}</span> certifications
                    {searchQuery && ` for "${searchQuery}"`}
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    {Object.entries(certsByProvider).map(([provider, certs]) => (
                      <Badge key={provider} variant="secondary">
                        {providerLabels[provider] || provider}: {certs.length}
                      </Badge>
                    ))}
                  </div>
                </div>

                <Tabs defaultValue="all" className="space-y-6">
                  <TabsList>
                    <TabsTrigger value="all">All Certifications</TabsTrigger>
                    {Object.keys(certsByProvider).map((provider) => (
                      <TabsTrigger key={provider} value={provider}>
                        {providerLabels[provider] || provider}
                      </TabsTrigger>
                    ))}
                  </TabsList>

                  <TabsContent value="all">
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {filteredCerts.map((cert) => (
                        <CertificationCard key={cert.id} certification={cert} />
                      ))}
                    </div>
                  </TabsContent>

                  {Object.entries(certsByProvider).map(([provider, certs]) => (
                    <TabsContent key={provider} value={provider}>
                      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {certs.map((cert) => (
                          <CertificationCard key={cert.id} certification={cert} />
                        ))}
                      </div>
                    </TabsContent>
                  ))}
                </Tabs>
              </>
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <Award className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <h2 className="text-xl font-semibold mb-2">No certifications found</h2>
                  <p className="text-muted-foreground mb-4">
                    Try adjusting your search or filters
                  </p>
                  <Button variant="outline" onClick={clearFilters}>
                    Clear Filters
                  </Button>
                </CardContent>
              </Card>
            )}

            <div className="mt-12 grid md:grid-cols-2 gap-8">
              <Card>
                <CardHeader>
                  <CardTitle>Why Get Certified?</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                      <span className="text-green-600 font-bold">1</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Career Advancement</h4>
                      <p className="text-sm text-muted-foreground">
                        Certifications can lead to promotions and higher salaries
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                      <span className="text-blue-600 font-bold">2</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Industry Recognition</h4>
                      <p className="text-sm text-muted-foreground">
                        Validate your skills with globally recognized credentials
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
                      <span className="text-purple-600 font-bold">3</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Skill Validation</h4>
                      <p className="text-sm text-muted-foreground">
                        Prove your expertise to employers and peers
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Popular Certification Paths</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button 
                    variant="outline" 
                    className="w-full justify-start"
                    onClick={() => { setSelectedProvider('aws'); handleSearch() }}
                  >
                    <Award className="mr-2 h-4 w-4 text-orange-500" />
                    AWS Certification Path
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full justify-start"
                    onClick={() => { setSelectedProvider('comptia'); handleSearch() }}
                  >
                    <Award className="mr-2 h-4 w-4 text-red-500" />
                    CompTIA Security+ Path
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full justify-start"
                    onClick={() => { setSelectedProvider('hashicorp'); handleSearch() }}
                  >
                    <Award className="mr-2 h-4 w-4 text-black" />
                    HashiCorp Infrastructure Path
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full justify-start"
                    onClick={() => router.push('/courses')}
                  >
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Browse Courses First
                  </Button>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
