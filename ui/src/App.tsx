import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Layout } from "@/components/Layout"
import LogsPage from "@/pages/LogsPage"
import AssistantsPage from "@/pages/AssistantsPage"
import ThreadsPage from "@/pages/ThreadsPage"
import MemoryPage from "@/pages/MemoryPage"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<LogsPage />} />
          <Route path="assistants" element={<AssistantsPage />} />
          <Route path="threads" element={<ThreadsPage />} />
          <Route path="memory" element={<MemoryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
