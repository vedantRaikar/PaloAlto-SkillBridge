import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Star, Clock, Users, ExternalLink, Play } from 'lucide-react'

interface CourseCardProps {
  course: {
    id: string
    title: string
    provider?: string
    url: string
    instructor?: string
    duration_hours?: number
    rating?: number
    num_students?: number
    price?: number
    is_free: boolean
    level?: string
    thumbnail_url?: string
    description?: string
  }
  compact?: boolean
}

const providerColors: Record<string, string> = {
  udemy: 'bg-purple-500',
  coursera: 'bg-blue-500',
  youtube: 'bg-red-500',
  edx: 'bg-green-500',
  pluralsight: 'bg-orange-500',
  udacity: 'bg-blue-600',
  linkedin_learning: 'bg-blue-700',
}

const providerLogos: Record<string, string> = {
  udemy: 'U',
  coursera: 'C',
  youtube: 'YT',
  edx: 'e',
  pluralsight: 'PS',
}

export function CourseCard({ course, compact = false }: CourseCardProps) {
  const providerColor = (course.provider && providerColors[course.provider]) || 'bg-gray-500'
  const isYouTube = course.provider === 'youtube'
  const providerName = course.provider?.toUpperCase() || 'COURSE'

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow">
      {course.thumbnail_url && !compact && (
        <div className="relative h-40 bg-gray-100">
          <img
            src={course.thumbnail_url}
            alt={course.title}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
          {isYouTube && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/30">
              <div className="w-12 h-12 bg-red-500 rounded-full flex items-center justify-center">
                <Play className="w-6 h-6 text-white ml-1" />
              </div>
            </div>
          )}
          <Badge className={`absolute top-2 right-2 ${providerColor} text-white`}>
            {providerName}
          </Badge>
        </div>
      )}
      
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className={`text-sm font-semibold line-clamp-2 ${compact ? '' : 'leading-tight'}`}>
            {course.title}
          </CardTitle>
          {!course.thumbnail_url && (
            <Badge variant="outline" className={`${providerColor} text-white text-xs shrink-0`}>
              {providerName}
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-3">
        {course.instructor && !compact && (
          <p className="text-sm text-muted-foreground truncate">
            by {course.instructor}
          </p>
        )}
        
        <div className="flex flex-wrap gap-2 text-xs">
          {course.duration_hours && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {course.duration_hours < 1 
                ? `${Math.round(course.duration_hours * 60)}min`
                : `${course.duration_hours}h`}
            </Badge>
          )}
          
          {course.rating && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
              {course.rating.toFixed(1)}
            </Badge>
          )}
          
          {course.num_students && !compact && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {course.num_students > 1000 
                ? `${(course.num_students / 1000).toFixed(1)}k`
                : course.num_students}
            </Badge>
          )}
          
          {course.level && course.level !== 'all_levels' && (
            <Badge variant="outline" className="capitalize">
              {course.level}
            </Badge>
          )}
        </div>
        
        {!compact && course.description && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {course.description}
          </p>
        )}
        
        <div className="flex items-center justify-between pt-2 border-t">
          <div>
            {course.is_free ? (
              <span className="text-green-600 font-semibold text-sm">Free</span>
            ) : course.price ? (
              <span className="font-semibold text-sm">${course.price}</span>
            ) : (
              <span className="text-muted-foreground text-sm">Price varies</span>
            )}
          </div>
          
          <Button size="sm" asChild>
            <a 
              href={course.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-1"
            >
              {isYouTube ? <Play className="w-3 h-3" /> : <ExternalLink className="w-3 h-3" />}
              {isYouTube ? 'Watch' : 'View'}
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function CourseCardSkeleton() {
  return (
    <Card className="overflow-hidden">
      <div className="h-40 bg-gray-200 animate-pulse" />
      <CardHeader className="pb-2">
        <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-3 bg-gray-200 rounded animate-pulse w-1/2" />
        <div className="flex gap-2">
          <div className="h-6 w-16 bg-gray-200 rounded animate-pulse" />
          <div className="h-6 w-16 bg-gray-200 rounded animate-pulse" />
        </div>
      </CardContent>
    </Card>
  )
}
