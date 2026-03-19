'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { roadmapApi, type GraphNode, type GraphEdge, type GraphStats } from '@/lib/api'
import { 
  ZoomIn, ZoomOut, RotateCcw, Maximize2, Filter, 
  Loader2, Info, Layers, Network, Target
} from 'lucide-react'

interface KnowledgeGraphVisualizerProps {
  className?: string
  onNodeClick?: (node: GraphNode) => void
  initialType?: string
  initialCategory?: string
}

interface ForceGraphNode extends GraphNode {
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number
  fy?: number
}

interface ForceGraphLink {
  source: string | ForceGraphNode
  target: string | ForceGraphNode
  type: string
}

const nodeColors: Record<string, string> = {
  role: '#8b5cf6',
  skill: '#3b82f6',
  course: '#22c55e',
  certification: '#f97316',
  domain: '#6b7280',
  user: '#ec4899',
  default: '#9ca3af',
}

const linkColors: Record<string, string> = {
  REQUIRES: '#8b5cf6',
  TEACHES: '#22c55e',
  PART_OF: '#6b7280',
  RELATED_TO: '#f97316',
  default: '#9ca3af',
}

export function KnowledgeGraphVisualizer({
  className = '',
  onNodeClick,
  initialType,
  initialCategory,
}: KnowledgeGraphVisualizerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()
  const nodesRef = useRef<ForceGraphNode[]>([])
  const linksRef = useRef<ForceGraphLink[]>([])
  const velocityRef = useRef<{ x: number; y: number }[]>([])
  
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [edges, setEdges] = useState<GraphEdge[]>([])
  const [stats, setStats] = useState<GraphStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState<string | null>(initialType || null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const [hoveredNode, setHoveredNode] = useState<ForceGraphNode | null>(null)
  const [selectedNode, setSelectedNode] = useState<ForceGraphNode | null>(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [draggedNode, setDraggedNode] = useState<ForceGraphNode | null>(null)
  const [isPanning, setIsPanning] = useState(false)
  const [lastMouse, setLastMouse] = useState({ x: 0, y: 0 })

  const fetchGraphData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await roadmapApi.getGraph({
        type: filterType || undefined,
        limit: 200,
      })
      setNodes(data.nodes)
      setEdges(data.edges)
      setStats(data.stats)
      
      nodesRef.current = data.nodes.map(n => ({ ...n }))
      linksRef.current = data.edges.map(e => ({ ...e }))
      velocityRef.current = data.nodes.map(() => ({ x: 0, y: 0 }))
      
      initializePositions()
    } catch (error) {
      console.error('Failed to fetch graph data:', error)
    } finally {
      setLoading(false)
    }
  }, [filterType])

  useEffect(() => {
    fetchGraphData()
  }, [fetchGraphData])

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    }
    
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  const initializePositions = () => {
    const centerX = dimensions.width / 2
    const centerY = dimensions.height / 2
    const radius = Math.min(dimensions.width, dimensions.height) / 3

    nodesRef.current.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / nodesRef.current.length
      node.x = centerX + radius * Math.cos(angle) + (Math.random() - 0.5) * 50
      node.y = centerY + radius * Math.sin(angle) + (Math.random() - 0.5) * 50
      velocityRef.current[i] = { x: 0, y: 0 }
    })
  }

  const simulateForces = useCallback(() => {
    const alpha = 0.1
    const repulsion = 500
    const attraction = 0.01
    const centering = 0.01
    const centerX = dimensions.width / 2
    const centerY = dimensions.height / 2

    velocityRef.current.forEach((v, i) => {
      const node = nodesRef.current[i]
      if (!node || draggedNode?.id === node.id) return

      let fx = 0, fy = 0

      nodesRef.current.forEach((other, j) => {
        if (i === j) return
        const dx = (node.x || 0) - (other.x || 0)
        const dy = (node.y || 0) - (other.y || 0)
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = repulsion / (dist * dist)
        fx += (dx / dist) * force
        fy += (dy / dist) * force
      })

      linksRef.current.forEach(link => {
        const sourceId = typeof link.source === 'string' ? link.source : link.source.id
        const targetId = typeof link.target === 'string' ? link.target : link.target.id
        
        if (sourceId === node.id) {
          const target = nodesRef.current.find(n => n.id === targetId)
          if (target) {
            fx += ((target.x || 0) - (node.x || 0)) * attraction
            fy += ((target.y || 0) - (node.y || 0)) * attraction
          }
        } else if (targetId === node.id) {
          const source = nodesRef.current.find(n => n.id === sourceId)
          if (source) {
            fx += ((source.x || 0) - (node.x || 0)) * attraction
            fy += ((source.y || 0) - (node.y || 0)) * attraction
          }
        }
      })

      fx += (centerX - (node.x || 0)) * centering
      fy += (centerY - (node.y || 0)) * centering

      v.x = (v.x + fx * alpha) * 0.9
      v.y = (v.y + fy * alpha) * 0.9

      node.x = Math.max(20, Math.min(dimensions.width - 20, (node.x || 0) + v.x))
      node.y = Math.max(20, Math.min(dimensions.height - 20, (node.y || 0) + v.y))
    })
  }, [dimensions, draggedNode])

  const render = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, dimensions.width, dimensions.height)
    ctx.save()
    ctx.translate(pan.x, pan.y)
    ctx.scale(zoom, zoom)

    linksRef.current.forEach(link => {
      const source = nodesRef.current.find(n => n.id === (typeof link.source === 'string' ? link.source : link.source.id))
      const target = nodesRef.current.find(n => n.id === (typeof link.target === 'string' ? link.target : link.target.id))
      
      if (source?.x && source?.y && target?.x && target?.y) {
        ctx.beginPath()
        ctx.moveTo(source.x, source.y)
        ctx.lineTo(target.x, target.y)
        ctx.strokeStyle = linkColors[link.type] || linkColors.default
        ctx.lineWidth = 1
        ctx.globalAlpha = 0.4
        ctx.stroke()
        ctx.globalAlpha = 1
      }
    })

    nodesRef.current.forEach(node => {
      if (!node.x || !node.y) return
      
      const isHovered = hoveredNode?.id === node.id
      const isSelected = selectedNode?.id === node.id
      const radius = (isHovered || isSelected) ? 10 : 7
      const color = nodeColors[node.type] || nodeColors.default

      ctx.beginPath()
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
      ctx.fillStyle = color
      ctx.fill()
      
      if (isHovered || isSelected) {
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 2
        ctx.stroke()
      }

      if (isHovered || isSelected) {
        ctx.fillStyle = '#1f2937'
        ctx.font = '12px sans-serif'
        ctx.textAlign = 'center'
        ctx.fillText(node.title, node.x, node.y - 15)
      }
    })

    ctx.restore()
  }, [dimensions, zoom, pan, hoveredNode, selectedNode])

  const animate = useCallback(() => {
    simulateForces()
    render()
    animationRef.current = requestAnimationFrame(animate)
  }, [simulateForces, render])

  useEffect(() => {
    animationRef.current = requestAnimationFrame(animate)
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current)
    }
  }, [animate])

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    
    const x = (e.clientX - rect.left - pan.x) / zoom
    const y = (e.clientY - rect.top - pan.y) / zoom

    if (isDragging && draggedNode) {
      draggedNode.x = x
      draggedNode.y = y
      draggedNode.fx = x
      draggedNode.fy = y
      return
    }

    if (isPanning) {
      setPan(prev => ({
        x: prev.x + (e.clientX - rect.left - lastMouse.x),
        y: prev.y + (e.clientY - rect.top - lastMouse.y),
      }))
      setLastMouse({ x: e.clientX - rect.left, y: e.clientY - rect.top })
      return
    }

    const hovered = nodesRef.current.find(node => {
      if (!node.x || !node.y) return false
      const dx = node.x - x
      const dy = node.y - y
      return Math.sqrt(dx * dx + dy * dy) < 10
    })
    setHoveredNode(hovered || null)
  }

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    
    if (e.button === 0 && hoveredNode) {
      setIsDragging(true)
      setDraggedNode(hoveredNode)
    } else if (e.button === 1 || e.button === 2) {
      setIsPanning(true)
      setLastMouse({ x: e.clientX - rect.left, y: e.clientY - rect.top })
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
    setIsPanning(false)
    if (draggedNode) {
      draggedNode.fx = undefined
      draggedNode.fy = undefined
    }
    setDraggedNode(null)
  }

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (hoveredNode) {
      setSelectedNode(selectedNode?.id === hoveredNode.id ? null : hoveredNode)
      onNodeClick?.(hoveredNode)
    }
  }

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    setZoom(z => Math.max(0.2, Math.min(3, z * delta)))
  }

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault()
  }

  const zoomIn = () => setZoom(z => Math.min(3, z * 1.2))
  const zoomOut = () => setZoom(z => Math.max(0.2, z / 1.2))
  const resetView = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
    initializePositions()
  }

  const nodeTypes = ['role', 'skill', 'course', 'certification']

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Network className="h-5 w-5" />
            Knowledge Graph
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={zoomOut}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-sm font-medium w-16 text-center">{Math.round(zoom * 100)}%</span>
            <Button variant="outline" size="sm" onClick={zoomIn}>
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={resetView}>
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        <div className="flex items-center gap-2 mt-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          {nodeTypes.map(type => (
            <Badge
              key={type}
              variant={filterType === type ? 'default' : 'outline'}
              className="cursor-pointer capitalize"
              style={{ 
                backgroundColor: filterType === type ? nodeColors[type] : 'transparent',
                borderColor: nodeColors[type],
                color: filterType === type ? 'white' : nodeColors[type],
              }}
              onClick={() => setFilterType(filterType === type ? null : type)}
            >
              {type}
            </Badge>
          ))}
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <div 
          ref={containerRef} 
          className="relative bg-slate-50 rounded-b-lg"
          style={{ height: 500 }}
        >
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <canvas
              ref={canvasRef}
              width={dimensions.width}
              height={dimensions.height}
              className="cursor-grab active:cursor-grabbing"
              onMouseMove={handleMouseMove}
              onMouseDown={handleMouseDown}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onClick={handleClick}
              onWheel={handleWheel}
              onContextMenu={handleContextMenu}
            />
          )}
          
          {stats && (
            <div className="absolute bottom-4 left-4 bg-white/90 rounded-lg p-3 text-xs space-y-1 shadow-md">
              <div className="font-semibold flex items-center gap-1">
                <Info className="h-3 w-3" /> Stats
              </div>
              <div className="grid grid-cols-2 gap-x-4">
                <span className="text-muted-foreground">Nodes:</span>
                <span className="font-medium">{stats.total_nodes}</span>
                <span className="text-muted-foreground">Edges:</span>
                <span className="font-medium">{stats.total_edges}</span>
                <span className="text-muted-foreground">Roles:</span>
                <span className="font-medium">{stats.roles}</span>
                <span className="text-muted-foreground">Skills:</span>
                <span className="font-medium">{stats.skills}</span>
              </div>
            </div>
          )}
          
          {selectedNode && (
            <div className="absolute top-4 right-4 bg-white rounded-lg p-4 shadow-lg max-w-xs">
              <h3 className="font-semibold flex items-center gap-2">
                <Target className="h-4 w-4" style={{ color: nodeColors[selectedNode.type] }} />
                {selectedNode.title}
              </h3>
              <Badge variant="outline" className="mt-2 capitalize">
                {selectedNode.type}
              </Badge>
              {selectedNode.category && (
                <p className="text-sm text-muted-foreground mt-2">
                  Category: {selectedNode.category}
                </p>
              )}
              <Button 
                variant="ghost" 
                size="sm" 
                className="mt-2 w-full"
                onClick={() => setSelectedNode(null)}
              >
                Close
              </Button>
            </div>
          )}
          
          <div className="absolute bottom-4 right-4 bg-white/90 rounded-lg p-2 shadow-md flex gap-2">
            <div className="flex items-center gap-1 text-xs">
              {Object.entries(nodeColors).slice(0, 5).map(([type, color]) => (
                <div key={type} className="flex items-center gap-1">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: color }}
                  />
                  <span className="capitalize text-muted-foreground">{type}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
