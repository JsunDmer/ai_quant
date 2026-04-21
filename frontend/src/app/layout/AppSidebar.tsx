import { useEffect, useRef, useState } from 'react';
import { apiPost, apiGet } from '../../api/client';
import type { CreateJobResponse, JobResponse, JobStatus } from '../../api/types';
import type { ChartPalette } from '../../charts/chartTokens';
import { TrendingUp, Building2, Search, FileText, PanelLeft, PanelLeftClose, Sun, Moon } from 'lucide-react';

export type NavKey = 'market' | 'sectors' | 'signals' | 'evaluation';

const NAV_ICONS: Record<NavKey, React.ReactNode> = {
  market: <TrendingUp size={18} />,
  sectors: <Building2 size={18} />,
  signals: <Search size={18} />,
  evaluation: <FileText size={18} />,
};

export function AppSidebar(props: {
  active: NavKey;
  onNavigate: (key: NavKey) => void;
  onMarketRefresh: () => void;
  collapsed?: boolean;
  onToggleSidebar: () => void;
  chartPalette: ChartPalette;
  onChangeChartPalette: (palette: ChartPalette) => void;
}) {
  const collapsed = props.collapsed;

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
      } catch {
        setJobError('轮询失败，请稍后再试');
        if (pollingRef.current) window.clearInterval(pollingRef.current);
      }
    }, 1500);
  };

  const onRunAnalysis = async () => {
    setJobError(null);
    try {
      const r = await apiPost<CreateJobResponse>('/api/jobs/analysis', {
        // 默认触发完整链路：新闻采集 -> AI分析 -> 板块推荐 -> 个股信号
        ai_enabled: true,
        refresh_realtime_only: false,
      });
      setJobId(r.task_id);
      setJobStatus(r.status);
      startPolling(r.task_id);
    } catch {
      setJobError('触发失败，请确认后端服务已启动');
    }
  };

  const allNavItems = [
    { key: 'market' as NavKey, label: '市场分析', icon: NAV_ICONS.market },
    { key: 'sectors' as NavKey, label: '板块分析', icon: NAV_ICONS.sectors },
    { key: 'signals' as NavKey, label: '个股分析', icon: NAV_ICONS.signals },
    { key: 'evaluation' as NavKey, label: '评估报告', icon: NAV_ICONS.evaluation },
  ];

  const chartPaletteButtons = (compact: boolean) => (
    <div
      style={
        compact
          ? { display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }
          : { display: 'flex', gap: 8 }
      }
    >
      <ChartPaletteBtn
        compact={compact}
        active={props.chartPalette === 'light'}
        onClick={() => props.onChangeChartPalette('light')}
        label="浅色"
        icon={<Sun size={compact ? 16 : 15} />}
        ariaLabel="浅色模式"
      />
      <ChartPaletteBtn
        compact={compact}
        active={props.chartPalette === 'dark'}
        onClick={() => props.onChangeChartPalette('dark')}
        label="深色"
        icon={<Moon size={compact ? 16 : 15} />}
        ariaLabel="深色模式"
      />
    </div>
  );

  if (collapsed) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minHeight: 0,
          width: '100%',
        }}
      >
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            alignItems: 'center',
            paddingTop: 48,
            overflow: 'auto',
          }}
        >
          {allNavItems.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => props.onNavigate(item.key)}
              style={{
                width: 40,
                height: 40,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: props.active === item.key ? 'var(--bg-secondary)' : 'transparent',
                border: props.active === item.key ? '1px solid var(--border-color)' : '1px solid transparent',
                borderRadius: 10,
                cursor: 'pointer',
                fontSize: 18,
                color: 'var(--text-primary)',
                transition: 'background 0.18s ease, border-color 0.18s ease',
              }}
              title={item.label}
            >
              {item.icon}
            </button>
          ))}
        </div>

        <div
          style={{
            flexShrink: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            alignItems: 'center',
            paddingTop: 12,
            paddingBottom: 4,
            borderTop: '1px solid var(--border-color)',
          }}
        >
          {chartPaletteButtons(true)}
          <button
            type="button"
            onClick={props.onToggleSidebar}
            aria-label="展开侧栏"
            title="展开侧栏"
            style={{
              width: 40,
              height: 40,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 10,
              border: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              transition: 'background 0.18s ease, border-color 0.18s ease, color 0.18s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--bg-tertiary)';
              e.currentTarget.style.color = 'var(--text-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--bg-secondary)';
              e.currentTarget.style.color = 'var(--text-secondary)';
            }}
          >
            <PanelLeft size={18} strokeWidth={2} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        flex: 1,
        minHeight: 0,
        width: '100%',
      }}
    >
      <div>
        <div style={{ fontWeight: 700, fontSize: 14 }}>股民间投资助手</div>
        <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-secondary)' }}>盘后数据 · 板块与个股信号</div>
      </div>

      <div style={{ borderTop: '1px solid var(--border-color)' }} />

      {allNavItems.map((item) => (
        <NavItem
          key={item.key}
          active={props.active === item.key}
          onClick={() => props.onNavigate(item.key)}
          icon={item.icon}
        >
          {item.label}
        </NavItem>
      ))}

      <div style={{ borderTop: '1px solid var(--border-color)', marginTop: 4 }} />

      <SectionTitle>执行分析</SectionTitle>
      <button
        type="button"
        onClick={onRunAnalysis}
        disabled={isRunning}
        className="primary-btn"
        style={{
          width: '100%',
          border: 'none',
          borderRadius: 10,
          padding: '12px 16px',
          background: 'var(--accent-blue)',
          color: '#fff',
          fontSize: 13,
          fontWeight: 600,
          cursor: isRunning ? 'not-allowed' : 'pointer',
          transition: 'all 0.25s ease',
          opacity: isRunning ? 0.7 : 1,
        }}
      >
        {isRunning ? '执行中…' : '执行完整分析'}
      </button>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
        状态：{jobStatus ?? '—'} {jobId ? `(${jobId.slice(0, 6)})` : ''}
      </div>
      {jobError ? <div style={{ fontSize: 12, color: 'var(--accent-red)' }}>{jobError}</div> : null}

      <div style={{ flex: 1, minHeight: 16 }} />

      <div
        style={{
          borderTop: '1px solid var(--border-color)',
          paddingTop: 12,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        <SectionTitle>界面主题</SectionTitle>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4, marginTop: -4 }}>
          切换网页的深浅模式。
        </div>
        {chartPaletteButtons(false)}
        <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          当前：{props.chartPalette === 'dark' ? '深色模式' : '浅色模式'}
        </div>

        <button
          type="button"
          onClick={props.onToggleSidebar}
          aria-label="收起侧栏"
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            marginTop: 4,
            padding: '10px 12px',
            borderRadius: 10,
            border: '1px solid var(--border-color)',
            background: 'var(--bg-secondary)',
            color: 'var(--text-secondary)',
            fontSize: 13,
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'background 0.18s ease, border-color 0.18s ease, color 0.18s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-tertiary)';
            e.currentTarget.style.color = 'var(--text-primary)';
            e.currentTarget.style.borderColor = 'var(--border-strong)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--bg-secondary)';
            e.currentTarget.style.color = 'var(--text-secondary)';
            e.currentTarget.style.borderColor = 'var(--border-color)';
          }}
        >
          <PanelLeftClose size={18} strokeWidth={2} />
          <span>收起侧栏</span>
        </button>
      </div>
    </div>
  );
}

function ChartPaletteBtn(props: {
  compact: boolean;
  active: boolean;
  onClick: () => void;
  label: string;
  icon: React.ReactNode;
  ariaLabel: string;
}) {
  if (props.compact) {
    return (
      <button
        type="button"
        aria-label={props.ariaLabel}
        aria-pressed={props.active}
        title={props.label}
        onClick={props.onClick}
        style={{
          width: 40,
          height: 40,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 10,
          border: props.active ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
          background: props.active ? 'color-mix(in srgb, var(--accent-blue) 12%, transparent)' : 'var(--bg-secondary)',
          color: props.active ? 'var(--accent-blue)' : 'var(--text-secondary)',
          cursor: 'pointer',
          transition: 'border-color 0.18s ease, background 0.18s ease, color 0.18s ease',
        }}
      >
        {props.icon}
      </button>
    );
  }
  return (
    <button
      type="button"
      aria-pressed={props.active}
      onClick={props.onClick}
      style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        padding: '9px 10px',
        borderRadius: 10,
        border: props.active ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
        background: props.active ? 'color-mix(in srgb, var(--accent-blue) 10%, transparent)' : 'var(--bg-secondary)',
        color: props.active ? 'var(--accent-blue)' : 'var(--text-secondary)',
        fontSize: 12,
        fontWeight: props.active ? 600 : 500,
        cursor: 'pointer',
        transition: 'border-color 0.18s ease, background 0.18s ease, color 0.18s ease',
      }}
    >
      {props.icon}
      <span>{props.label}</span>
    </button>
  );
}

function SectionTitle(props: { children: string }) {
  return <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)' }}>{props.children}</div>;
}

function NavItem(props: { active: boolean; onClick: () => void; children: string; icon: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        textAlign: 'left',
        background: props.active ? 'var(--bg-secondary)' : 'transparent',
        color: props.active ? 'var(--text-primary)' : 'var(--text-secondary)',
        border: props.active ? `1px solid var(--border-color)` : '1px solid transparent',
        borderRadius: 10,
        padding: '12px 12px',
        fontSize: 13,
        fontWeight: props.active ? 600 : 400,
        cursor: 'pointer',
        transition: 'background 0.18s ease, border-color 0.18s ease, color 0.18s ease',
      }}
      onMouseEnter={(e) => {
        if (!props.active) {
          e.currentTarget.style.background = 'var(--bg-secondary)';
        }
      }}
      onMouseLeave={(e) => {
        if (!props.active) {
          e.currentTarget.style.background = 'transparent';
        }
      }}
    >
      <span
        style={{
          display: 'flex',
          alignItems: 'center',
          color: props.active ? 'var(--accent-blue)' : 'var(--text-secondary)',
          transition: 'color 0.18s ease',
        }}
      >
        {props.icon}
      </span>
      {props.children}
    </button>
  );
}
