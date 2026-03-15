import { useEffect, useState } from "react"
import { Bot, Trash2, RefreshCw, ChevronRight, Brain } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { type Assistant, listAssistants, deleteAssistant } from "@/lib/api"
import { useNavigate } from "react-router-dom"

export default function AssistantsPage() {
  const [assistants, setAssistants] = useState<Assistant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const navigate = useNavigate()

  async function load() {
    setLoading(true)
    setError("")
    try {
      const data = await listAssistants()
      const list = Array.isArray(data) ? data : (data as any).assistants ?? (data as any).data ?? []
      setAssistants(list)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id: string) {
    if (!confirm("Delete this assistant and all its threads/memories?")) return
    try {
      await deleteAssistant(id)
      setAssistants((prev) => prev.filter((a) => (a.assistant_id ?? a.id) !== id))
    } catch (e: any) {
      setError(e.message)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-border px-5 py-3">
        <Bot className="h-4 w-4 text-violet-400" />
        <h1 className="text-sm font-semibold">Assistants</h1>
        <span className="text-xs text-muted-foreground">
          {assistants.length} total
        </span>
        <div className="ml-auto">
          <Button size="sm" variant="ghost" onClick={load} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-5 mt-3 rounded-md bg-red-900/30 border border-red-800/50 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* List */}
      <div className="flex-1 overflow-y-auto log-scroll">
        {loading && assistants.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            Loading assistants…
          </div>
        ) : assistants.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            No assistants found
          </div>
        ) : (
          <div className="divide-y divide-border">
            {assistants.map((a) => {
              const id = a.assistant_id ?? (a as any).id ?? ""
              return (
                <div
                  key={id}
                  className="flex items-center gap-3 px-5 py-3 hover:bg-accent/20 transition-colors group"
                >
                  <Bot className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{a.name || id}</span>
                      {a.name?.startsWith("tribal-") && (
                        <Badge variant="graph">project</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-xs text-muted-foreground font-mono truncate">{id}</span>
                      {a.embedding_model && (
                        <span className="text-xs text-muted-foreground">
                          {a.embedding_model}
                        </span>
                      )}
                      {a.created_at && (
                        <span className="text-xs text-muted-foreground">
                          {new Date(a.created_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-violet-400"
                    onClick={() => navigate(`/?assistant=${id}`)}
                    title="View memories"
                  >
                    <Brain className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400"
                    onClick={() => handleDelete(id)}
                    title="Delete assistant"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                  <ChevronRight className="h-4 w-4 text-muted-foreground/50" />
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
