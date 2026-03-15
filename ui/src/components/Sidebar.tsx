import { useState, useEffect } from "react"
import { NavLink } from "react-router-dom"
// eslint-disable-next-line deprecation/deprecation
import { Brain, Bot, Sun, Moon, Github, BookOpen } from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { to: "/", icon: Brain, label: "Memory" },
  { to: "/assistants", icon: Bot, label: "Assistants" },
] as const

function useTheme() {
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem("theme")
    if (stored) return stored === "dark"
    return document.documentElement.classList.contains("dark")
  })

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
    localStorage.setItem("theme", dark ? "dark" : "light")
  }, [dark])

  return [dark, () => setDark((d) => !d)] as const
}

export function Sidebar() {
  const [dark, toggleTheme] = useTheme()

  return (
    <aside className="flex h-full w-52 shrink-0 flex-col border-r border-border bg-card">
      {/* Brand */}
      <div className="flex items-center gap-2 px-4 py-4 border-b border-border">
        <img src="/logo.svg" alt="TribalMind" className="h-5 w-5" />
        <span className="font-semibold tracking-tight text-sm">TribalMind</span>
      </div>

      {/* Nav links */}
      <nav className="flex flex-col gap-0.5 px-2 py-3">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end
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

      {/* Bottom */}
      <div className="mt-auto border-t border-border px-3 py-3 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <a
            href="https://github.com/zachary-nguyen/TribalMind"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-colors"
            aria-label="GitHub"
          >
            <Github className="h-3.5 w-3.5" />
          </a>
          <a
            href="https://tribalmind.dev/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-colors"
            aria-label="Documentation"
          >
            <BookOpen className="h-3.5 w-3.5" />
          </a>
        </div>
        <button
          onClick={toggleTheme}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-colors"
          aria-label="Toggle theme"
        >
          {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
        </button>
      </div>
    </aside>
  )
}
