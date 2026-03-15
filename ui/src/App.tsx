import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Layout } from "@/components/Layout"
import AssistantsPage from "@/pages/AssistantsPage"
import MemoryPage from "@/pages/MemoryPage"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<MemoryPage />} />
          <Route path="assistants" element={<AssistantsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
