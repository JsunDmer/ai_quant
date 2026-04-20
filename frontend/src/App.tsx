import { useEffect, useMemo, useState } from 'react'
import './App.css'
import {
  applyThemeMode,
  getStoredThemeMode,
  setThemeMode,
  watchSystemTheme,
  type ThemeMode,
} from './theme/theme'

function App() {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => getStoredThemeMode())

  useEffect(() => {
    applyThemeMode(themeMode)
    if (themeMode !== 'system') return
    return watchSystemTheme(() => applyThemeMode('system'))
  }, [themeMode])

  const themeLabel = useMemo(() => {
    if (themeMode === 'light') return '浅色'
    if (themeMode === 'dark') return '深色'
    return '系统'
  }, [themeMode])

  const onChangeTheme = (mode: ThemeMode) => {
    setThemeMode(mode)
    setThemeModeState(mode)
  }

  return (
    <>
      <div style={{ padding: 24 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontWeight: 600 }}>股民间投资助手（React）</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>主题：{themeLabel}</span>
            <select
              value={themeMode}
              onChange={(e) => onChangeTheme(e.target.value as ThemeMode)}
              style={{
                background: 'var(--bg-card)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
                padding: '6px 8px',
              }}
            >
              <option value="system">系统</option>
              <option value="light">浅色</option>
              <option value="dark">深色</option>
            </select>
          </div>
        </div>

        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
          }}
        >
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            前端工程已初始化。下一步会接入侧边栏导航、API 拉取与 ECharts。
          </div>
        </div>
      </div>
    </>
  )
}

export default App
