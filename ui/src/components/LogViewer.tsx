import { useEffect, useRef } from "react"
import { Badge } from "@/components/ui/badge"

export interface LogEntry {
  id: string
  raw: string
  timestamp: string
  level: string
  module: string
  message: string
  isGraph: boolean
}

// 2024-01-01 12:00:00,123 [INFO] tribalmind.daemon.server: message
const LOG_RE = /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) \[(\w+)\] ([^:]+): (.+)$/

export function parseLine(raw: string): LogEntry {
  const m = LOG_RE.exec(raw)
  if (!m) {
    return { id: crypto.randomUUID(), raw, timestamp: "", level: "INFO", module: "", message: raw, isGraph: false }
  }
  const [, timestamp, level, module, message] = m
  return {
    id: crypto.randomUUID(),
    raw,
    timestamp,
    level: level.toUpperCase(),
    module,
    message,
    isGraph: message.startsWith("graph:"),
  }
}

type LevelBadgeVariant = "debug" | "info" | "warning" | "error" | "graph" | "default"

function levelVariant(level: string, isGraph: boolean): LevelBadgeVariant {
  if (isGraph) return "graph"
  switch (level) {
    case "DEBUG": return "debug"
    case "INFO": return "info"
    case "WARNING":
    case "WARN": return "warning"
    case "ERROR":
    case "CRITICAL": return "error"
    default: return "default"
  }
}

function shortModule(module: string): string {
  const parts = module.split(".")
  return parts[parts.length - 1] ?? module
}

interface LogViewerProps {
  entries: LogEntry[]
  autoScroll: boolean
}

export function LogViewer({ entries, autoScroll }: LogViewerProps) {
  const topRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (autoScroll && topRef.current) {
      topRef.current.scrollIntoView({ behavior: "instant" })
    }
  }, [entries, autoScroll])

  if (entries.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground text-sm">
        No log entries yet — start the daemon with{" "}
        <code className="mx-1.5 rounded bg-secondary px-1.5 py-0.5 font-mono text-xs">tribal start</code>
      </div>
    )
  }

  const reversed = [...entries].reverse()

  return (
    <div className="log-scroll flex-1 overflow-y-auto font-mono text-xs">
      <div ref={topRef} />
      <table className="w-full border-collapse">
        <tbody>
          {reversed.map((entry) => (
            <tr
              key={entry.id}
              className="border-b border-border/30 hover:bg-accent/20 transition-colors"
            >
              {/* Timestamp */}
              <td className="py-0.5 pl-3 pr-4 text-muted-foreground whitespace-nowrap align-top">
                {entry.timestamp ? entry.timestamp.slice(11, 23) : ""}
              </td>

              {/* Level badge */}
              <td className="py-0.5 pr-3 align-top whitespace-nowrap">
                <Badge variant={levelVariant(entry.level, entry.isGraph)}>
                  {entry.isGraph ? "GRAPH" : entry.level}
                </Badge>
              </td>

              {/* Module */}
              <td className="py-0.5 pr-4 text-muted-foreground whitespace-nowrap align-top">
                {shortModule(entry.module)}
              </td>

              {/* Message */}
              <td className="py-0.5 pr-3 break-all align-top text-foreground/90">
                {entry.isGraph
                  ? <GraphMessage message={entry.message} />
                  : entry.message}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Highlights key=value pairs inside graph node log messages. */
function GraphMessage({ message }: { message: string }) {
  // e.g. "graph: monitor: cmd='pip install foo' exit=1 error=True"
  const parts = message.split(/(\w+=\S+)/)
  return (
    <span className="text-violet-300/90">
      {parts.map((part, i) =>
        /^\w+=/.test(part)
          ? <span key={i} className="text-violet-200">{part}</span>
          : part
      )}
    </span>
  )
}
