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
  } | null;
};

export type MarketLatestResponse = {
  trade_date: string;
  status: string;
  indices: unknown[];
  market_breadth: Record<string, unknown>;
  turnover: Record<string, unknown>;
  north_flow: Record<string, unknown>;
  news: unknown[];
  created_at: string;
};

