import { useEffect, useState, useMemo } from "react"
import { useSearchParams } from "react-router-dom"
import { Brain, Trash2, RefreshCw, Search, Tag, Bookmark, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  type Assistant,
  type Memory,
  listAssistants,
  listMemories,
  searchMemories,
  deleteMemory,
  clearMemories,
} from "@/lib/api"

/** Parse the TribalMind JSON memory format, with legacy fallback. */
function parseMemory(content: string) {
  // Try JSON first (new format)
  try {
    const data = JSON.parse(content)
    if (typeof data === "object" && data !== null) {
      return {
        category: data.category ?? "",
        subject: data.subject ?? data.package ?? "",
        content: data.content ?? data.fix_text ?? data.error_text ?? "",
      }
    }
  } catch {
    // Fall back to legacy pipe-delimited format
  }

  const catMatch = content.match(/^\[(\w+)\]/)
  const category = catMatch?.[1] ?? ""
  const pkg = content.match(/package=([\w.\-]+)/)?.[1] ?? ""
  const fixMatch = content.match(/fix:\s*(.+?)(?:\s*\||$)/)
  const fix = fixMatch?.[1]?.trim() ?? ""
  const pipes = content.split("|")
  const errorText = pipes.length >= 2 ? pipes[1].trim() : ""

  return {
    category,
    subject: pkg,
    content: fix || errorText || content,
  }
}

function categoryVariant(cat: string) {
  switch (cat) {
    case "fix": return "error"
    case "convention": return "info"
    case "architecture": return "graph"
    case "context": return "secondary"
    case "decision": return "warning"
    case "tip": return "success"
    default: return "default"
  }
}

export default function MemoryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [assistants, setAssistants] = useState<Assistant[]>([])
  const [selectedAssistant, setSelectedAssistant] = useState(searchParams.get("assistant") ?? "")
  const [memories, setMemories] = useState<Memory[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingAssistants, setLoadingAssistants] = useState(true)
  const [error, setError] = useState("")
  const [query, setQuery] = useState("")
  const [isSearchMode, setIsSearchMode] = useState(false)
  const [filterCategory, setFilterCategory] = useState<string>("ALL")

  // Load assistants for the picker
  useEffect(() => {
    (async () => {
      try {
        const data = await listAssistants()
        const list = Array.isArray(data) ? data : (data as any).assistants ?? (data as any).data ?? []
        setAssistants(list)
        // Auto-select first if none selected
        if (!selectedAssistant && list.length > 0) {
          const first = list[0].assistant_id ?? list[0].id ?? ""
          setSelectedAssistant(first)
        }
      } catch (e: any) {
        setError(e.message)
      } finally {
        setLoadingAssistants(false)
      }
    })()
  }, [])

  // Load memories when assistant changes
  useEffect(() => {
    if (!selectedAssistant) return
    loadMemories()
  }, [selectedAssistant])

  async function loadMemories() {
    if (!selectedAssistant) return
    setLoading(true)
    setError("")
    setIsSearchMode(false)
    try {
      const data = await listMemories(selectedAssistant)
      const list = Array.isArray(data) ? data : (data as any).memories ?? (data as any).data ?? []
      setMemories(list)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleSearch() {
    if (!selectedAssistant || !query.trim()) return
    setLoading(true)
    setError("")
    setIsSearchMode(true)
    try {
      const data = await searchMemories(selectedAssistant, query.trim())
      const list = Array.isArray(data) ? data : (data as any).memories ?? (data as any).data ?? []
      setMemories(list)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(memoryId: string) {
    if (!confirm("Delete this memory?")) return
    try {
      await deleteMemory(selectedAssistant, memoryId)
      setMemories((prev) => prev.filter((m) => (m.memory_id ?? m.id) !== memoryId))
    } catch (e: any) {
      setError(e.message)
    }
  }

  // Extract unique categories for filter
  const categories = useMemo(() => {
    const cats = new Set<string>()
    memories.forEach((m) => {
      const { category } = parseMemory(m.content)
      if (category) cats.add(category)
    })
    return ["ALL", ...Array.from(cats).sort()]
  }, [memories])

  const filtered = useMemo(() => {
    if (filterCategory === "ALL") return memories
    return memories.filter((m) => parseMemory(m.content).category === filterCategory)
  }, [memories, filterCategory])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-border px-5 py-3">
        <Brain className="h-4 w-4 text-violet-400" />
        <h1 className="text-sm font-semibold">Memory</h1>
        <span className="text-xs text-muted-foreground">
          {filtered.length} {isSearchMode ? "results" : "memories"}
        </span>

        <div className="ml-auto flex items-center gap-2">
          {/* Assistant picker */}
          <select
            value={selectedAssistant}
            onChange={(e) => {
              setSelectedAssistant(e.target.value)
              setSearchParams(e.target.value ? { assistant: e.target.value } : {})
            }}
            className="h-7 rounded-md border border-border bg-secondary px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            disabled={loadingAssistants}
          >
            <option value="">Select assistant…</option>
            {assistants.map((a) => {
              const id = a.assistant_id ?? (a as any).id ?? ""
              return (
                <option key={id} value={id}>
                  {a.name || id}
                </option>
              )
            })}
          </select>

          <Button
            size="sm"
            variant="ghost"
            className="text-muted-foreground hover:text-red-400"
            onClick={async () => {
              if (!selectedAssistant) return
              if (!confirm(`Clear ALL ${memories.length} memories for this assistant?`)) return
              setLoading(true)
              try {
                await clearMemories(selectedAssistant)
                setMemories([])
                setError("")
              } catch (e: any) {
                setError(e.message)
              } finally {
                setLoading(false)
              }
            }}
            disabled={loading || !selectedAssistant || memories.length === 0}
          >
            <XCircle className="h-3.5 w-3.5" />
            Clear All
          </Button>
          <Button size="sm" variant="ghost" onClick={loadMemories} disabled={loading || !selectedAssistant}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Search + filters bar */}
      <div className="flex items-center gap-2 border-b border-border px-5 py-2">
        <form
          className="relative flex items-center"
          onSubmit={(e) => {
            e.preventDefault()
            handleSearch()
          }}
        >
          <Search className="pointer-events-none absolute left-2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Semantic search…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-7 rounded-md border border-border bg-secondary pl-7 pr-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring w-64"
          />
          <Button size="sm" variant="ghost" type="submit" className="ml-1" disabled={!query.trim()}>
            Search
          </Button>
          <span className="ml-1 text-[10px] text-muted-foreground/60" title="Semantic search uses a RAG query — each search is a billed Backboard operation">
            (billed per query)
          </span>
        </form>

        {isSearchMode && (
          <Button size="sm" variant="ghost" onClick={loadMemories}>
            Clear search
          </Button>
        )}

        <div className="mx-2 h-4 w-px bg-border" />

        {/* Category filters */}
        <div className="flex items-center gap-1">
          {categories.map((cat) => (
            <Button
              key={cat}
              size="sm"
              variant={filterCategory === cat ? "active" : "ghost"}
              onClick={() => setFilterCategory(cat)}
            >
              {cat}
            </Button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mx-5 mt-3 rounded-md bg-red-900/30 border border-red-800/50 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Memory list */}
      <div className="flex-1 overflow-y-auto log-scroll">
        {loading && memories.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            Loading memories…
          </div>
        ) : !selectedAssistant ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            Select an assistant to view memories
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            {isSearchMode ? "No results found" : "No memories stored yet"}
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filtered.map((m) => {
              const id = m.memory_id ?? m.id ?? ""
              const parsed = parseMemory(m.content)
              const score = m.score

              return (
                <div
                  key={id}
                  className="px-5 py-3 hover:bg-accent/20 transition-colors group"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      {/* Tags row */}
                      <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                        {parsed.category && (
                          <Badge variant={categoryVariant(parsed.category) as any}>
                            <Tag className="mr-1 h-2.5 w-2.5" />
                            {parsed.category}
                          </Badge>
                        )}
                        {parsed.subject && (
                          <Badge variant="secondary">
                            <Bookmark className="mr-1 h-2.5 w-2.5" />
                            {parsed.subject}
                          </Badge>
                        )}
                        {score != null && (
                          <Badge variant="graph">
                            sim {(score as number).toFixed(3)}
                          </Badge>
                        )}
                      </div>

                      {/* Content */}
                      {parsed.content && (
                        <p className="text-xs text-foreground/90 leading-relaxed">
                          {parsed.content}
                        </p>
                      )}

                      {/* Raw content (collapsed) */}
                      <details className="mt-1">
                        <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                          Raw content
                        </summary>
                        <pre className="mt-1 text-xs text-foreground/70 bg-secondary/50 rounded p-2 whitespace-pre-wrap break-all font-mono">
                          {m.content}
                        </pre>
                      </details>

                      {/* Metadata */}
                      <div className="flex items-center gap-3 mt-1.5">
                        <span className="text-xs text-muted-foreground font-mono">{id.slice(0, 12)}</span>
                        {m.created_at && (
                          <span className="text-xs text-muted-foreground">
                            {new Date(m.created_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Delete */}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 shrink-0"
                      onClick={() => handleDelete(id)}
                      title="Delete memory"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
