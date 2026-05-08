import { useEffect, useState } from 'react'
import './App.css'
import { AppLayout } from './app/layout/AppLayout'
import { AppSidebar, type NavKey } from './app/layout/AppSidebar'
import { MarketPage } from './pages/MarketPage'
import { SectorsPage } from './pages/SectorsPage'
import { SignalsPage } from './pages/SignalsPage'
import { EvaluationPage } from './pages/EvaluationPage'
import { ErrorBoundary } from './components/ErrorBoundary'
import type { ChartPalette } from './charts/chartTokens'

function App() {
  const [chartPalette, setChartPalette] = useState<ChartPalette>(() => {
    const v = window.localStorage.getItem('ai_quant_chart_palette');
    if (v === 'light' || v === 'dark') return v;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  })
  const [active, setActive] = useState<NavKey>('market')
  const [analysisRefreshKey, setAnalysisRefreshKey] = useState(0)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  useEffect(() => {
    window.localStorage.setItem('ai_quant_chart_palette', chartPalette)
    document.documentElement.setAttribute('data-theme', chartPalette)
    document.documentElement.style.colorScheme = chartPalette
  }, [chartPalette])

  return (
    <AppLayout
      collapsed={sidebarCollapsed}
      sidebar={
        <AppSidebar
          active={active}
          onNavigate={setActive}
          onMarketRefresh={() => setAnalysisRefreshKey((k) => k + 1)}
          collapsed={sidebarCollapsed}
          onToggleSidebar={() => setSidebarCollapsed((c) => !c)}
          chartPalette={chartPalette}
          onChangeChartPalette={setChartPalette}
        />
      }
    >
      <ErrorBoundary key={active}>
        <div className="page-enter">
          {active === 'market' ? <MarketPage refreshKey={analysisRefreshKey} chartPalette={chartPalette} /> : null}
          {active === 'sectors' ? <SectorsPage refreshKey={analysisRefreshKey} /> : null}
          {active === 'signals' ? <SignalsPage refreshKey={analysisRefreshKey} /> : null}
          {active === 'evaluation' ? <EvaluationPage refreshKey={analysisRefreshKey} /> : null}
        </div>
      </ErrorBoundary>
    </AppLayout>
  )
}

export default App
