import { useEffect, useState, useCallback } from "react"
import { Activity, RefreshCw, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { type ActivityEvent, getActivity, clearActivity } from "@/lib/api"

const ACTION_FILTERS = ["all", "remember", "recall", "forget"] as const
type ActionFilter = (typeof ACTION_FILTERS)[number]

function actionVariant(action: string) {
  switch (action) {
    case "remember":
      return "success"
    case "recall":
      return "info"
    case "forget":
      return "error"
    default:
      return "secondary"
  }
}

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export default function ActivityPage() {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [filter, setFilter] = useState<ActionFilter>("all")

  const load = useCallback(async (actionFilter: ActionFilter = filter) => {
    setLoading(true)
    setError("")
    try {
      const data = await getActivity(200, 0, actionFilter === "all" ? "" : actionFilter)
      setEvents(data)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    load(filter)
  }, [filter])

  async function handleClear() {
    if (!confirm("Clear the entire activity log? This cannot be undone.")) return
    setLoading(true)
    try {
      await clearActivity()
      setEvents([])
      setError("")
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-border px-5 py-3">
        <Activity className="h-4 w-4 text-cyan-400" />
        <h1 className="text-sm font-semibold">Activity Log</h1>
        <span className="text-xs text-muted-foreground">
          {events.length} events
        </span>

        <div className="ml-auto flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            className="text-muted-foreground hover:text-red-400"
            onClick={handleClear}
            disabled={loading || events.length === 0}
          >
            <XCircle className="h-3.5 w-3.5" />
            Clear Log
          </Button>
          <Button size="sm" variant="ghost" onClick={() => load()} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-1 border-b border-border px-5 py-2">
        {ACTION_FILTERS.map((f) => (
          <Button
            key={f}
            size="sm"
            variant={filter === f ? "active" : "ghost"}
            onClick={() => setFilter(f)}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </Button>
        ))}
      </div>

      {error && (
        <div className="mx-5 mt-3 rounded-md bg-red-900/30 border border-red-800/50 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Event list */}
      <div className="flex-1 overflow-y-auto log-scroll">
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            Loading activity…
          </div>
        ) : events.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            No activity recorded yet
          </div>
        ) : (
          <div className="divide-y divide-border">
            {events.map((evt, i) => (
              <div
                key={`${evt.timestamp}-${i}`}
                className="px-5 py-3 hover:bg-accent/20 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    {/* Action badge + timestamp */}
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={actionVariant(evt.action) as any}>
                        {evt.action}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatTime(evt.timestamp)}
                      </span>
                      {evt.source && (
                        <Badge variant="secondary">{evt.source}</Badge>
                      )}
                    </div>

                    {/* Summary */}
                    <p className="text-xs text-foreground/90 leading-relaxed">
                      {evt.summary}
                    </p>

                    {/* Metadata row */}
                    <div className="flex items-center gap-3 mt-1.5">
                      {evt.count != null && evt.count > 0 && (
                        <span className="text-xs text-muted-foreground">
                          {evt.count} {evt.action === "recall" ? "results" : "memories"}
                        </span>
                      )}
                      {evt.memory_id && (
                        <span className="text-xs text-muted-foreground font-mono">
                          {evt.memory_id.slice(0, 12)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
