import { useState } from 'react'
import './App.css'
import { AppLayout } from './app/layout/AppLayout'
import { AppSidebar, type NavKey } from './app/layout/AppSidebar'
import { MarketPage } from './pages/MarketPage'
import { SectorsPage } from './pages/SectorsPage'
import { SignalsPage } from './pages/SignalsPage'
import { EvaluationPage } from './pages/EvaluationPage'

function App() {
  const [active, setActive] = useState<NavKey>('market')
  const [marketRefreshKey, setMarketRefreshKey] = useState(0)

  return (
    <AppLayout
      sidebar={
        <AppSidebar
          active={active}
          onNavigate={setActive}
          onMarketRefresh={() => setMarketRefreshKey((k) => k + 1)}
        />
      }
    >
      {active === 'market' ? <MarketPage refreshKey={marketRefreshKey} /> : null}
      {active === 'sectors' ? <SectorsPage /> : null}
      {active === 'signals' ? <SignalsPage /> : null}
      {active === 'evaluation' ? <EvaluationPage /> : null}
    </AppLayout>
  )
}

export default App
