import { useEffect, useRef, useState } from "react"
import { Activity, CircleDot, Pause, Play, RotateCcw, Search, Wifi, WifiOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { LogViewer, parseLine, type LogEntry } from "@/components/LogViewer"

type LevelFilter = "ALL" | "DEBUG" | "INFO" | "WARNING" | "ERROR"

const LEVEL_FILTERS: LevelFilter[] = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR"]
const MAX_ENTRIES = 2000

interface DaemonStatus {
  running: boolean
  pid: number | null
}

export default function App() {
  const [entries, setEntries] = useState<LogEntry[]>([])
  const [filter, setFilter] = useState<LevelFilter>("ALL")
  const [search, setSearch] = useState("")
  const [autoScroll, setAutoScroll] = useState(true)
  const [connected, setConnected] = useState(false)
  const [daemon, setDaemon] = useState<DaemonStatus | null>(null)
  const esRef = useRef<EventSource | null>(null)

  // SSE connection with exponential backoff
  useEffect(() => {
    let retryDelay = 1000
    let retryTimer: ReturnType<typeof setTimeout> | null = null

    function connect() {
      const es = new EventSource("/api/logs")
      esRef.current = es

      es.onopen = () => {
        setConnected(true)
        retryDelay = 1000 // reset backoff on success
      }

      es.onmessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data as string) as { type: string; line?: string; message?: string }
        if (data.type === "log" && data.line) {
          const entry = parseLine(data.line)
          setEntries((prev) => {
            const next = [...prev, entry]
            return next.length > MAX_ENTRIES ? next.slice(-MAX_ENTRIES) : next
          })
        }
      }

      es.onerror = () => {
        setConnected(false)
        es.close()
        retryTimer = setTimeout(() => {
          retryDelay = Math.min(retryDelay * 2, 30000) // cap at 30 s
          connect()
        }, retryDelay)
      }
    }

    connect()
    return () => {
      esRef.current?.close()
      if (retryTimer) clearTimeout(retryTimer)
    }
  }, [])

  // Poll daemon status — slows to 15 s when backend is unreachable
  useEffect(() => {
    let delay = 5000
    let timer: ReturnType<typeof setTimeout> | null = null

    async function check() {
      try {
        const res = await fetch("/api/status")
        const data = (await res.json()) as DaemonStatus
        setDaemon(data)
        delay = 5000
      } catch {
        setDaemon(null)
        delay = 15000
      }
      timer = setTimeout(check, delay)
    }

    check()
    return () => { if (timer) clearTimeout(timer) }
  }, [])

  // Filter entries
  const visible = entries.filter((e) => {
    if (filter !== "ALL" && e.level !== filter && !(filter === "WARNING" && e.level === "WARN")) {
      return false
    }
    if (search) {
      const q = search.toLowerCase()
      return e.message.toLowerCase().includes(q) || e.module.toLowerCase().includes(q)
    }
    return true
  })

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      {/* ── Header ── */}
      <header className="flex shrink-0 items-center gap-3 border-b border-border px-4 py-2.5">
        <Activity className="h-4 w-4 text-teal-400" />
        <span className="font-semibold tracking-tight">TribalMind</span>
        <span className="text-muted-foreground text-sm">Live Logs</span>

        <div className="ml-auto flex items-center gap-2">
          {/* SSE connection dot */}
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            {connected
              ? <Wifi className="h-3.5 w-3.5 text-green-400" />
              : <WifiOff className="h-3.5 w-3.5 text-red-400" />}
            {connected ? "Connected" : "Reconnecting…"}
          </span>

          {/* Daemon status */}
          {daemon && (
            <Badge variant={daemon.running ? "success" : "error"}>
              <CircleDot className="mr-1 h-2.5 w-2.5" />
              {daemon.running ? `Daemon · PID ${daemon.pid}` : "Daemon stopped"}
            </Badge>
          )}
        </div>
      </header>

      {/* ── Toolbar ── */}
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2">
        {/* Level filters */}
        <div className="flex items-center gap-1">
          {LEVEL_FILTERS.map((lf) => (
            <Button
              key={lf}
              size="sm"
              variant={filter === lf ? "active" : "ghost"}
              onClick={() => setFilter(lf)}
            >
              {lf}
            </Button>
          ))}
        </div>

        <div className="mx-2 h-4 w-px bg-border" />

        {/* Search */}
        <div className="relative flex items-center">
          <Search className="pointer-events-none absolute left-2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Filter messages…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-7 rounded-md border border-border bg-secondary pl-7 pr-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring w-52"
          />
        </div>

        {/* Entry count */}
        <span className="ml-1 text-xs text-muted-foreground">
          {visible.length}/{entries.length}
        </span>

        <div className="ml-auto flex items-center gap-1.5">
          {/* Auto-scroll toggle */}
          <Button
            size="sm"
            variant={autoScroll ? "active" : "ghost"}
            onClick={() => setAutoScroll((v) => !v)}
            title={autoScroll ? "Pause auto-scroll" : "Resume auto-scroll"}
          >
            {autoScroll ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            {autoScroll ? "Live" : "Paused"}
          </Button>

          {/* Clear */}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setEntries([])}
            title="Clear log display"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Clear
          </Button>
        </div>
      </div>

      {/* ── Log list ── */}
      <LogViewer entries={visible} autoScroll={autoScroll} />
    </div>
  )
}
