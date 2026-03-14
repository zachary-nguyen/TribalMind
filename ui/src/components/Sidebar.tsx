import { NavLink } from "react-router-dom"
import { Activity, Brain, MessageSquare, Bot } from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { to: "/", icon: Activity, label: "Logs" },
  { to: "/assistants", icon: Bot, label: "Assistants" },
  { to: "/threads", icon: MessageSquare, label: "Threads" },
  { to: "/memory", icon: Brain, label: "Memory" },
] as const

export function Sidebar() {
  return (
    <aside className="flex h-full w-52 shrink-0 flex-col border-r border-border bg-card">
      {/* Brand */}
      <div className="flex items-center gap-2 px-4 py-4 border-b border-border">
        <Activity className="h-5 w-5 text-violet-400" />
        <span className="font-semibold tracking-tight text-sm">TribalMind</span>
      </div>

      {/* Nav links */}
      <nav className="flex flex-col gap-0.5 px-2 py-3">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Bottom spacer */}
      <div className="mt-auto border-t border-border px-4 py-3">
        <span className="text-xs text-muted-foreground">Backboard Dashboard</span>
      </div>
    </aside>
  )
}
