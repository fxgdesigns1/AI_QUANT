import Dashboard from './Dashboard'
import VMTradeJournal from './components/VMTradeJournal'
import ControlPlaneDashboard from './components/ControlPlaneDashboard'
import SystemStatusBadge from './components/SystemStatusBadge'

function App() {
  const path = window.location.pathname;

  if (path === '/vm') {
    return <VMTradeJournal />
  }

  if (path === '/control') {
    return (
      <>
        <SystemStatusBadge />
        <ControlPlaneDashboard />
      </>
    )
  }

  return (
    <>
      <SystemStatusBadge />
      <Dashboard />
    </>
  )
}

export default App
