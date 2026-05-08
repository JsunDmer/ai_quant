export type ThemeMode = 'light' | 'dark' | 'system';

export type JobStatus = 'queued' | 'running' | 'success' | 'failed';

export type CreateJobResponse = {
  task_id: string;
  status: JobStatus;
};

export type JobResponse = {
  task_id: string;
  status: JobStatus;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  error: string | null;
  result_summary: {
    status?: string;
    trade_date?: string;
    data_date?: string;
    errors?: string[];
    diagnostics?: Record<string, unknown>;
    diagnostics_summary?: {
      has_stock_signals?: boolean;
      no_reco_reason_codes?: string[];
      stage_errors?: Array<{ stage: string; error: string }>;
      candidate_counts?: {
        selected_sector_count?: number;
        before_auction?: number;
        after_auction?: number;
        after_financial?: number;
        auction_filtered?: number;
        financial_filtered?: number;
      };
      signal_counts?: {
        candidates_input?: number;
        kline_success_count?: number;
        kline_insufficient_count?: number;
        buy_signal_count?: number;
      };
    };
    no_reco_reason_codes?: string[];
  } | null;
};

export type MarketLatestResponse = {
  trade_date: string;
  status: string;
  indices: unknown[];
  market_breadth: Record<string, unknown>;
  turnover: Record<string, unknown>;
  north_flow: Record<string, unknown>;
  market_movers?: unknown[];
  watchlist_size?: number;
  news: unknown[];
  created_at: string;
};

export type SignalRealtimeInfo = {
  price: number;
  pre_close: number;
  change_percent: number;
  change_amount: number;
  source: string;
};

export type SignalAuctionInfo = {
  has_data: boolean;
  tag: string;
  pct_change: number;
  volume_ratio: number;
  trade_date: string;
  source: string;
};

export type SignalItem = {
  trade_date: string;
  stock_code: string;
  stock_name: string;
  sector_name: string;
  signal: string;
  confidence: number;
  factors: unknown[];
  realtime: SignalRealtimeInfo;
  auction: SignalAuctionInfo;
  created_at: string;
};

export type SignalsLatestResponse = {
  trade_date: string | null;
  items: SignalItem[];
};

export type KlineItem = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type KlineResponse = {
  stock_code: string;
  data: KlineItem[];
};

export type FinancialData = {
  stock_code: string;
  has_data: boolean;
  net_profit: number;
  net_profit_yoy: number;
  roe: number;
  reason: string;
};

