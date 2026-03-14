import { useEffect, useState } from "react"
import { MessageSquare, Trash2, RefreshCw, ChevronDown, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { type Thread, type ThreadMessage, listThreads, getThread, deleteThread } from "@/lib/api"

export default function ThreadsPage() {
  const [threads, setThreads] = useState<Thread[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ThreadMessage[]>([])
  const [loadingMessages, setLoadingMessages] = useState(false)

  async function load() {
    setLoading(true)
    setError("")
    try {
      const data = await listThreads()
      const list = Array.isArray(data) ? data : (data as any).threads ?? (data as any).data ?? []
      setThreads(list)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function toggleExpand(threadId: string) {
    if (expandedId === threadId) {
      setExpandedId(null)
      setMessages([])
      return
    }
    setExpandedId(threadId)
    setLoadingMessages(true)
    try {
      const detail = await getThread(threadId)
      setMessages(detail.messages ?? [])
    } catch {
      setMessages([])
    } finally {
      setLoadingMessages(false)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this thread?")) return
    try {
      await deleteThread(id)
      setThreads((prev) => prev.filter((t) => (t.thread_id ?? t.id) !== id))
      if (expandedId === id) setExpandedId(null)
    } catch (e: any) {
      setError(e.message)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-border px-5 py-3">
        <MessageSquare className="h-4 w-4 text-violet-400" />
        <h1 className="text-sm font-semibold">Threads</h1>
        <span className="text-xs text-muted-foreground">
          {threads.length} total
        </span>
        <div className="ml-auto">
          <Button size="sm" variant="ghost" onClick={load} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="mx-5 mt-3 rounded-md bg-red-900/30 border border-red-800/50 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* List */}
      <div className="flex-1 overflow-y-auto log-scroll">
        {loading && threads.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            Loading threads…
          </div>
        ) : threads.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            No threads found
          </div>
        ) : (
          <div className="divide-y divide-border">
            {threads.map((t) => {
              const id = t.thread_id ?? t.id ?? ""
              const isExpanded = expandedId === id
              return (
                <div key={id}>
                  <div className="flex items-center gap-3 px-5 py-3 hover:bg-accent/20 transition-colors group">
                    <button
                      onClick={() => toggleExpand(id)}
                      className="shrink-0 text-muted-foreground hover:text-foreground"
                    >
                      {isExpanded
                        ? <ChevronDown className="h-4 w-4" />
                        : <ChevronRight className="h-4 w-4" />}
                    </button>
                    <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-mono truncate block">{id}</span>
                      <div className="flex items-center gap-3 mt-0.5">
                        {t.assistant_id && (
                          <span className="text-xs text-muted-foreground">
                            Assistant: <span className="font-mono">{t.assistant_id}</span>
                          </span>
                        )}
                        {t.created_at && (
                          <span className="text-xs text-muted-foreground">
                            {new Date(t.created_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400"
                      onClick={() => handleDelete(id)}
                      title="Delete thread"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>

                  {/* Expanded messages */}
                  {isExpanded && (
                    <div className="bg-card/50 border-t border-border px-5 py-3">
                      {loadingMessages ? (
                        <div className="text-xs text-muted-foreground py-2">Loading messages…</div>
                      ) : messages.length === 0 ? (
                        <div className="text-xs text-muted-foreground py-2">No messages in this thread</div>
                      ) : (
                        <div className="space-y-2 max-h-80 overflow-y-auto log-scroll">
                          {messages.map((msg, i) => (
                            <div key={i} className="flex gap-2">
                              <Badge variant={msg.role === "user" ? "info" : "graph"} className="shrink-0 mt-0.5">
                                {msg.role}
                              </Badge>
                              <p className="text-xs text-foreground/80 whitespace-pre-wrap break-all">
                                {msg.content}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
