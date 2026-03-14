import { Outlet } from "react-router-dom"
import { Sidebar } from "@/components/Sidebar"

export function Layout() {
  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <main className="flex flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
