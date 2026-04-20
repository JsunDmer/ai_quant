import { useEffect, useMemo, useRef, useState } from 'react';
import { apiPost, apiGet } from '../../api/client';
import type { CreateJobResponse, JobResponse, JobStatus } from '../../api/types';
import { applyThemeMode, getStoredThemeMode, setThemeMode, watchSystemTheme, type ThemeMode } from '../../theme/theme';

export type NavKey = 'market' | 'sectors' | 'signals' | 'evaluation';

export function AppSidebar(props: {
  active: NavKey;
  onNavigate: (key: NavKey) => void;
  onMarketRefresh: () => void;
}) {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => getStoredThemeMode());

  useEffect(() => {
    applyThemeMode(themeMode);
    if (themeMode !== 'system') return;
    return watchSystemTheme(() => applyThemeMode('system'));
  }, [themeMode]);

  const themeLabel = useMemo(() => {
    if (themeMode === 'light') return '浅色';
    if (themeMode === 'dark') return '深色';
    return '系统';
  }, [themeMode]);

  const onChangeTheme = (mode: ThemeMode) => {
    setThemeMode(mode);
    setThemeModeState(mode);
  };

  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const pollingRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (pollingRef.current) window.clearInterval(pollingRef.current);
    };
  }, []);

  const isRunning = jobStatus === 'queued' || jobStatus === 'running';

  const startPolling = (taskId: string) => {
    if (pollingRef.current) window.clearInterval(pollingRef.current);
    pollingRef.current = window.setInterval(async () => {
      try {
        const j = await apiGet<JobResponse>(`/api/jobs/${taskId}`);
        setJobStatus(j.status);
        if (j.status === 'failed') {
          setJobError(j.error ?? '执行失败');
          if (pollingRef.current) window.clearInterval(pollingRef.current);
        }
        if (j.status === 'success') {
          setJobError(null);
          if (pollingRef.current) window.clearInterval(pollingRef.current);
          props.onMarketRefresh();
        }
      } catch (e) {
        setJobError('轮询失败，请稍后再试');
        if (pollingRef.current) window.clearInterval(pollingRef.current);
      }
    }, 1500);
  };

  const onRunAnalysis = async () => {
    setJobError(null);
    try {
      const r = await apiPost<CreateJobResponse>('/api/jobs/analysis', {
        ai_enabled: false,
        refresh_realtime_only: true,
      });
      setJobId(r.task_id);
      setJobStatus(r.status);
      startPolling(r.task_id);
    } catch (e) {
      setJobError('触发失败，请确认后端服务已启动');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>股民间投资助手</div>
          <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-secondary)' }}>React + FastAPI</div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{themeLabel}</span>
          <select
            value={themeMode}
            onChange={(e) => onChangeTheme(e.target.value as ThemeMode)}
            aria-label="主题切换"
            style={{
              background: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: 6,
              padding: '6px 8px',
              fontSize: 12,
            }}
          >
            <option value="system">系统</option>
            <option value="light">浅色</option>
            <option value="dark">深色</option>
          </select>
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border-color)' }} />

      <NavItem active={props.active === 'market'} onClick={() => props.onNavigate('market')}>
        市场分析
      </NavItem>
      <NavItem active={props.active === 'sectors'} onClick={() => props.onNavigate('sectors')}>
        板块分析
      </NavItem>
      <NavItem active={props.active === 'signals'} onClick={() => props.onNavigate('signals')}>
        个股分析
      </NavItem>
      <NavItem active={props.active === 'evaluation'} onClick={() => props.onNavigate('evaluation')}>
        评估报告
      </NavItem>

      <div style={{ borderTop: '1px solid var(--border-color)', marginTop: 4 }} />

      <SectionTitle>执行分析</SectionTitle>
      <button
        onClick={onRunAnalysis}
        disabled={isRunning}
        style={{
          width: '100%',
          border: 'none',
          borderRadius: 6,
          padding: '10px 12px',
          background: 'var(--accent-blue)',
          color: '#fff',
          fontSize: 13,
          fontWeight: 600,
          cursor: isRunning ? 'not-allowed' : 'pointer',
          opacity: isRunning ? 0.7 : 1,
        }}
      >
        {isRunning ? '执行中…' : '执行分析'}
      </button>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
        状态：{jobStatus ?? '—'} {jobId ? `(${jobId.slice(0, 6)})` : ''}
      </div>
      {jobError ? (
        <div style={{ fontSize: 12, color: 'var(--accent-red)' }}>{jobError}</div>
      ) : null}

      {/* 预留：后续将数据源/AI/自动刷新等设置放在这里 */}
    </div>
  );
}

function SectionTitle(props: { children: string }) {
  return <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)' }}>{props.children}</div>;
}

function NavItem(props: { active: boolean; onClick: () => void; children: string }) {
  return (
    <button
      onClick={props.onClick}
      style={{
        width: '100%',
        textAlign: 'left',
        background: props.active ? 'var(--bg-secondary)' : 'transparent',
        color: props.active ? 'var(--text-primary)' : 'var(--text-secondary)',
        border: props.active ? `1px solid var(--border-color)` : '1px solid transparent',
        borderRadius: 8,
        padding: '10px 10px',
        fontSize: 13,
        cursor: 'pointer',
      }}
    >
      {props.children}
    </button>
  );
}

