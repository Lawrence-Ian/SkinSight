// src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import OnboardingPage from './pages/OnboardingPage'
import AuthPage       from './pages/AuthPage'
import DashboardPage  from './pages/DashboardPage'
import SkinAnalysisPage from './pages/SkinAnalysisPage'
import ResultPage     from './pages/ResultPage'
import RoutinePage    from './pages/RoutinePage'
import HistoryPage    from './pages/HistoryPage'
import ChatPage       from './pages/ChatPage'
import MapPage        from './pages/MapPage'
import ProfilePage    from './pages/ProfilePage'
import Layout         from './components/Layout'

function Guard({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="app-screen flex items-center justify-center bg-skin-bg">
      <div className="w-9 h-9 rounded-full border-4 border-skin-a2 border-t-transparent animate-spin" />
    </div>
  )
  return user ? children : <Navigate to="/auth" replace />
}

function AppRoutes() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/"         element={user ? <Navigate to="/dashboard"/> : <OnboardingPage/>} />
      <Route path="/auth"     element={user ? <Navigate to="/dashboard"/> : <AuthPage/>} />
      <Route path="/dashboard" element={<Guard><Layout><DashboardPage/></Layout></Guard>} />
      <Route path="/analysis" element={<Guard><Layout><SkinAnalysisPage/></Layout></Guard>} />
      <Route path="/result"   element={<Guard><Layout><ResultPage/></Layout></Guard>} />
      <Route path="/result/:scanId" element={<Guard><Layout><ResultPage/></Layout></Guard>} />
      <Route path="/history"  element={<Guard><Layout><HistoryPage/></Layout></Guard>} />
      <Route path="/routine" element={<Guard><Layout><RoutinePage/></Layout></Guard>} />
      <Route path="/chat"     element={<Guard><Layout><ChatPage/></Layout></Guard>} />
      <Route path="/map"      element={<Guard><Layout><MapPage/></Layout></Guard>} />
      <Route path="/profile"  element={<Guard><Layout><ProfilePage/></Layout></Guard>} />
      <Route path="*"         element={<Navigate to="/"/>} />
    </Routes>
  )
}

export default function App() {
  return <AuthProvider><AppRoutes /></AuthProvider>
}
