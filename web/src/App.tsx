import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { DataProvider } from './data'
import Layout from './components/Layout'
import Customer360 from './pages/Customer360'
import Portfolio from './pages/Portfolio'
import Pipeline from './pages/Pipeline'

export default function App() {
  return (
    <DataProvider>
      <HashRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/customer" replace />} />
            <Route path="/customer/:id?" element={<Customer360 />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/pipeline" element={<Pipeline />} />
            <Route path="*" element={<Navigate to="/customer" replace />} />
          </Route>
        </Routes>
      </HashRouter>
    </DataProvider>
  )
}
