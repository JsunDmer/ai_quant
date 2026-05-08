import { useEffect, useState } from 'react';
import { AlertCircle, BarChart2, TrendingDown, TrendingUp, Activity, Target } from 'lucide-react';
import { apiGet } from '../api/client';
import { PageHeader } from '../app/layout/PageHeader';

export function SectorsPage(props: { refreshKey: number }) {
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    apiGet<{ items: any[] }>('/api/sectors/latest')
      .then((d) => {
        if (!alive) return;
        setItems(d.items ?? []);
      })
      .catch(() => {
        if (!alive) return;
        setError('加载失败');
      });
    return () => {
      alive = false;
    };
  }, [props.refreshKey]);

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <PageHeader title="板块分析" subtitle="基于 AI 与动量的多维度板块轮动研判" />
      
      {error ? (
        <div className="ui-state ui-state--error" style={{ display: 'flex', alignItems: 'center', gap: 8, borderRadius: 'var(--radius-lg)' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      {!items && !error ? (
        <div className="ui-state ui-state--muted" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 18px', background: 'var(--bg-card)', backdropFilter: 'var(--glass-blur)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)' }}>
          <div
            style={{
              width: 20,
              height: 20,
              border: '2px solid var(--border-color)',
              borderTopColor: 'var(--accent-blue)',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }}
          />
          <style>{`
            @keyframes spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
          <span style={{ fontSize: 14, color: 'var(--text-secondary)', fontWeight: 500 }}>正在加载板块数据...</span>
        </div>
      ) : null}

      {items && items.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
          {items.slice(0, 20).map((it, idx) => {
            const name = it.sector_name ?? it.name ?? '—';
            const dir = String(it.direction ?? '').toLowerCase();
            const score = Number(it.rec_score) || 0;
            const conf = String(it.confidence ?? '—');
            const topStocks = Array.isArray(it.top_stocks) ? it.top_stocks : [];
            
            // 先按 direction 判断趋势，再用 rec_score 兜底，保证图标语义统一
            const trendByDirection =
              dir.includes('up') || dir.includes('上') || dir.includes('多') || dir.includes('强')
                ? 'up'
                : dir.includes('down') || dir.includes('下') || dir.includes('空') || dir.includes('弱')
                  ? 'down'
                  : null;
            const trend = trendByDirection ?? (score > 0 ? 'up' : score < 0 ? 'down' : 'neutral');
            const isUp = trend === 'up';
            const isDown = trend === 'down';
            
            const colorVar = isUp ? 'var(--accent-red)' : isDown ? 'var(--accent-green)' : 'var(--text-muted)';
            const bgVar = isUp ? 'var(--accent-red-dim)' : isDown ? 'var(--accent-green-dim)' : 'var(--bg-secondary)';
            const Icon = isUp ? TrendingUp : isDown ? TrendingDown : Activity;

            return (
              <div
                key={idx}
                className="surface-card"
                style={{
                  padding: '24px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 16,
                  position: 'relative',
                  overflow: 'hidden'
                }}
              >
                {/* Top color accent strip */}
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: colorVar }} />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ padding: 10, background: bgVar, borderRadius: 10, color: colorVar }}>
                      <Icon size={20} strokeWidth={2.5} />
                    </div>
                    <div style={{ fontWeight: 600, fontSize: 18, color: 'var(--text-primary)', letterSpacing: 0.5 }}>
                      {name}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 4 }}>
                  <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: 10 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', fontSize: 12, marginBottom: 4 }}>
                      <Target size={14} /> 置信度
                    </div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 15 }}>
                      {conf}
                    </div>
                  </div>
                  
                  <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: 10 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', fontSize: 12, marginBottom: 4 }}>
                      <BarChart2 size={14} /> 推荐得分
                    </div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 15, fontFamily: '"JetBrains Mono", monospace' }}>
                      {it.rec_score !== undefined ? Number(it.rec_score).toFixed(2) : '—'}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>推荐个股</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {String(it.stocks_source ?? '') === 'signal'
                        ? '来源：技术信号'
                        : String(it.stocks_source ?? '') === 'sector_candidate'
                          ? '来源：板块候选'
                        : String(it.stocks_source ?? '') === 'sector_cache'
                          ? '来源：板块成分股'
                          : '来源：暂无'}
                    </div>
                  </div>

                  {topStocks.length > 0 ? (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 8 }}>
                      {topStocks.slice(0, 4).map((stock: any, stockIdx: number) => {
                        const stockName = String(stock?.name ?? stock?.stock_name ?? '—');
                        const stockCode = String(stock?.code ?? stock?.stock_code ?? '');
                        const changeRaw = Number(stock?.change);
                        const hasChange = Number.isFinite(changeRaw);
                        const changeColor = hasChange ? (changeRaw > 0 ? 'var(--accent-red)' : changeRaw < 0 ? 'var(--accent-green)' : 'var(--text-muted)') : 'var(--text-muted)';
                        const changeText = hasChange ? `${changeRaw > 0 ? '+' : ''}${changeRaw.toFixed(2)}%` : '—';

                        return (
                          <div
                            key={`${stockCode || stockName}-${stockIdx}`}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: 10,
                              padding: '8px 10px',
                              borderRadius: 8,
                              background: 'var(--bg-secondary)',
                              border: '1px solid var(--border-color)',
                            }}
                          >
                            <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {stockName}
                              </div>
                              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: '"JetBrains Mono", monospace' }}>
                                {stockCode || '--'}
                              </div>
                            </div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: changeColor, fontFamily: '"JetBrains Mono", monospace' }}>
                              {changeText}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '10px 12px', borderRadius: 8, border: '1px dashed var(--border-color)', background: 'var(--bg-secondary)' }}>
                      暂无可用个股（可先执行一次完整分析后刷新）。
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}

      {items && items.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border-color)' }}>
          暂无板块分析数据。
        </div>
      ) : null}
    </div>
  );
}