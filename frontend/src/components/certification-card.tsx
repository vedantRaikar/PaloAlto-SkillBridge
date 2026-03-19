import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ExternalLink, Clock, Award, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'

interface CertificationCardProps {
  certification: {
    id?: string
    name: string
    short_name?: string
    provider?: string
    certification_url?: string
    level?: string
    cost_usd?: number
    validity_years?: number
    skills_covered?: string[]
    prerequisites?: string[]
    description?: string
    target_roles?: string[]
    renewal?: {
      required?: boolean
      period_years?: number
      requirements?: string
    }
    exam_details?: {
      duration_minutes?: number
      questions?: number
      format?: string
      passing_score?: string
    }
  }
  compact?: boolean
  showDetails?: boolean
}

const providerColors: Record<string, string> = {
  aws: 'bg-orange-500',
  gcp: 'bg-blue-500',
  azure: 'bg-blue-600',
  comptia: 'bg-red-500',
  isc2: 'bg-blue-700',
  isaca: 'bg-green-600',
  hashicorp: 'bg-black',
  google: 'bg-red-600',
  microsoft: 'bg-blue-500',
  oracle: 'bg-red-600',
  vmware: 'bg-gray-600',
  pmi: 'bg-orange-600',
  scrum: 'bg-green-500',
}

const levelColors: Record<string, string> = {
  fundamentals: 'bg-green-100 text-green-800 border-green-200',
  associate: 'bg-blue-100 text-blue-800 border-blue-200',
  professional: 'bg-purple-100 text-purple-800 border-purple-200',
  expert: 'bg-red-100 text-red-800 border-red-200',
  master: 'bg-yellow-100 text-yellow-800 border-yellow-200',
}

export function CertificationCard({ certification, compact = false, showDetails = false }: CertificationCardProps) {
  const providerColor = (certification.provider && providerColors[certification.provider]) || 'bg-gray-500'
  const levelColor = (certification.level && levelColors[certification.level]) || 'bg-gray-100 text-gray-800'

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Award className={`w-5 h-5 ${providerColor} text-white rounded p-0.5`} />
              <span className="text-xs font-medium text-muted-foreground uppercase">
                {certification.provider || 'Other'}
              </span>
            </div>
            <CardTitle className={`text-base font-semibold leading-tight ${compact ? 'line-clamp-2' : ''}`}>
              {certification.name}
            </CardTitle>
            {certification.short_name && (
              <p className="text-sm text-muted-foreground mt-1">
                {certification.short_name}
              </p>
            )}
          </div>
            <Badge className={`${levelColor} border capitalize shrink-0`}>
              {(certification.level || 'associate').replace('_', ' ')}
            </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-3 text-sm">
          {certification.cost_usd && (
            <div className="flex items-center gap-1">
              <span className="font-semibold">${certification.cost_usd}</span>
              <span className="text-muted-foreground">exam fee</span>
            </div>
          )}
          
          {certification.validity_years && certification.validity_years > 0 && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <Clock className="w-4 h-4" />
              <span>Valid {certification.validity_years} years</span>
            </div>
          )}
          
          {certification.renewal?.required ? (
            <Badge variant="outline" className="flex items-center gap-1 text-orange-600 border-orange-200">
              <RefreshCw className="w-3 h-3" />
              Renewal Required
            </Badge>
          ) : (
            <Badge variant="outline" className="flex items-center gap-1 text-green-600 border-green-200">
              <CheckCircle className="w-3 h-3" />
              Lifetime
            </Badge>
          )}
        </div>

        {!compact && (
          <>
            {certification.exam_details && (
              <div className="p-3 bg-gray-50 rounded-lg space-y-2 text-sm">
                <h4 className="font-medium text-xs uppercase text-muted-foreground">Exam Details</h4>
                <div className="grid grid-cols-2 gap-2">
                  {certification.exam_details.duration_minutes && (
                    <div>
                      <span className="text-muted-foreground">Duration:</span>{' '}
                      <span className="font-medium">{certification.exam_details.duration_minutes} min</span>
                    </div>
                  )}
                  {certification.exam_details.questions && (
                    <div>
                      <span className="text-muted-foreground">Questions:</span>{' '}
                      <span className="font-medium">{certification.exam_details.questions}</span>
                    </div>
                  )}
                  {certification.exam_details.format && (
                    <div className="col-span-2">
                      <span className="text-muted-foreground">Format:</span>{' '}
                      <span className="font-medium">{certification.exam_details.format}</span>
                    </div>
                  )}
                  {certification.exam_details.passing_score && (
                    <div>
                      <span className="text-muted-foreground">Passing:</span>{' '}
                      <span className="font-medium">{certification.exam_details.passing_score}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {(certification.skills_covered?.length ?? 0) > 0 && (
              <div>
                <h4 className="font-medium text-xs uppercase text-muted-foreground mb-2">
                  Skills Covered
                </h4>
                <div className="flex flex-wrap gap-1">
                  {(certification.skills_covered ?? []).slice(0, 6).map((skill: string) => (
                    <Badge key={skill} variant="secondary" className="text-xs capitalize">
                      {(skill || '').replace(/_/g, ' ')}
                    </Badge>
                  ))}
                  {(certification.skills_covered?.length ?? 0) > 6 && (
                    <Badge variant="outline" className="text-xs">
                      +{(certification.skills_covered?.length ?? 0) - 6} more
                    </Badge>
                  )}
                </div>
              </div>
            )}

            {(certification.target_roles?.length ?? 0) > 0 && !compact && (
              <div>
                <h4 className="font-medium text-xs uppercase text-muted-foreground mb-2">
                  Target Roles
                </h4>
                <div className="flex flex-wrap gap-1">
                  {(certification.target_roles ?? []).map((role: string) => (
                    <Badge key={role} variant="outline" className="text-xs">
                      {role}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {(certification.prerequisites?.length ?? 0) > 0 && (
              <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="flex items-center gap-2 text-yellow-800 mb-2">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">Prerequisites</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {(certification.prerequisites ?? []).map((prereq: string) => (
                    <Badge key={prereq} variant="secondary" className="text-xs bg-yellow-100">
                      {prereq}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
        
        <div className="pt-3 border-t">
          <Button size="sm" className="w-full" asChild>
            <a 
              href={certification.certification_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              Get Certified
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function CertificationCardSkeleton() {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="h-8 bg-gray-200 rounded animate-pulse w-3/4" />
        <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2 mt-2" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="h-4 bg-gray-200 rounded animate-pulse w-1/3" />
        <div className="h-16 bg-gray-200 rounded animate-pulse" />
        <div className="h-8 bg-gray-200 rounded animate-pulse" />
      </CardContent>
    </Card>
  )
}
