export type RaceDay = { date: string; rows: number };

export type SourceRow = {
  id: string;
  category: string;
  source: string;
  title: string;
  recordCount: number;
  updatedAt: string;
};

export type ScrapeSummary = {
  generatedAt?: string;
  raceDays: RaceDay[];
  sourceRows: SourceRow[];
};

export type RaceRow = {
  raceDate: string;
  racecourse: string;
  raceNo: number;
  raceIndex?: string;
  raceClass?: string;
  distanceM?: number;
  ratingRange?: string;
  going?: string;
  raceName?: string;
  prizeMoney?: string;
  surface?: string;
  courseLayout?: string;
  updatedAt?: string;
};

export type ResultRow = {
  raceDate: string;
  racecourse: string;
  raceNo: number;
  place: string;
  horseNo: string;
  horseName: string;
  horseCode: string | null;
  jockey: string;
  trainer: string;
  draw: string;
  lbw: string;
  finishTime: string;
  winOdds: string;
};

export type EntryRow = {
  raceDate: string;
  racecourse: string;
  raceNo: number;
  horseNo: string;
  horseName: string;
  horseCode: string | null;
  last6Runs?: string | null;
  actualWeight?: string | null;
  jockey?: string | null;
  draw?: string | null;
  trainer?: string | null;
  rating?: string | null;
  declaredHorseWeight?: string | null;
  daysSinceLastRun?: string | null;
  gear?: string | null;
  standby: number;
};

export type HorseFormRecord = {
  horseCode: string;
  raceIndex: string;
  place?: string | null;
  raceDate?: string | null;
  racecourse?: string | null;
  track?: string | null;
  course?: string | null;
  distanceM?: number | null;
  going?: string | null;
  raceClass?: string | null;
  draw?: string | null;
  rating?: string | null;
  trainer?: string | null;
  jockey?: string | null;
  lbw?: string | null;
  winOdds?: string | null;
  actualWeight?: string | null;
  runningPosition?: string | null;
  finishTime?: string | null;
  declaredHorseWeight?: string | null;
  gear?: string | null;
};

export type ChangeEventRow = {
  raceDate: string;
  raceNo: number;
  sequence: number;
  eventType: string;
  horseNo?: string | null;
  horseName?: string | null;
  relatedHorseName?: string | null;
  jockey?: string | null;
  declaredWeight?: string | null;
  eventTimeText?: string | null;
  description: string;
};

export type DividendRow = {
  raceDate: string;
  racecourse: string | null;
  raceNo: number;
  pool: string;
  winningCombination: string;
  dividend: string;
};

export type PredictionRow = {
  raceDate: string;
  racecourse: string;
  raceNo: number;
  horseCode: string;
  horseNo: string;
  horseName: string;
  modelName: string;
  modelVersion: string;
  trainingDatasetVersion?: string | null;
  featureVersion?: string | null;
  oddsMode?: string | null;
  dataBuildId?: string | null;
  winProbability: number;
  placeProbability: number;
  fairWinOdds: number | null;
  fairPlaceOdds: number | null;
  marketWinProbability: number | null;
  edge: number | null;
  isValueBet: boolean;
};

export type ScrapeJob = {
  raceDate: string;
  racecourse: string;
  status: string;
  attempts: number;
  startedAt?: string;
  finishedAt?: string;
  lastError?: string | null;
};

export type BacktestMetrics = {
  initialBankroll: number;
  finalBankroll: number;
  turnover: number;
  profitLoss: number;
  roi: number | null;
  hitRate: number | null;
  maxDrawdown: number;
  profitFactor: number | null;
  averageOdds: number | null;
  betCount: number;
};

export type BacktestBet = {
  sequence: number;
  race_date: string;
  racecourse: string;
  race_no: number;
  horse_code: string;
  horse_no: string;
  horse_name: string;
  bet_type: string;
  model_probability: number;
  market_probability: number | null;
  edge: number | null;
  stake: number;
  decimal_odds: number | null;
  payout: number;
  profit_loss: number;
  bankroll_after: number;
  is_hit: boolean;
};

export type BacktestEquityPoint = {
  sequence: number;
  race_date: string;
  racecourse: string;
  race_no: number;
  bankroll: number;
  drawdown: number;
};

export type BacktestCandidateExplanation = {
  raceDate?: string;
  race_date?: string;
  racecourse: string;
  raceNo?: number;
  race_no?: number;
  horseCode?: string;
  horse_code?: string;
  horseNo?: string;
  horse_no?: string;
  horseName?: string;
  horse_name?: string;
  betType?: string;
  bet_type?: string;
  status: "selected" | "filtered" | "not_selected";
  filterReason?: string | null;
  filter_reason?: string | null;
  modelProbability?: number;
  model_probability?: number;
  marketProbability?: number | null;
  market_probability?: number | null;
  fairOdds?: number | null;
  fair_odds?: number | null;
  edge: number | null;
};

export type BacktestReport = {
  config: Record<string, unknown>;
  metrics: BacktestMetrics;
  bets: BacktestBet[];
  equityCurve: BacktestEquityPoint[];
  candidateExplanations?: BacktestCandidateExplanation[];
  assumptions: string[];
};

export type OddsPoint = {
  legacyId: string;
  raceDate: string;
  raceNo: number;
  oddsType: string;
  oddsValue: string;
  odds: number;
  impliedProbability: number | null;
  betAmount: number | null;
  snapshotAt: string;
  source: string;
};

export type OddsSeries = {
  raceDate: string;
  raceNo: number;
  oddsType: string;
  oddsValue: string;
  snapshotCount: number;
  firstOdds: number | null;
  lastOdds: number | null;
  change: number | null;
  points: OddsPoint[];
};

export type OddsChangeReport = {
  raceDate: string;
  raceNo: number;
  oddsType: string;
  series: OddsSeries[];
};

export async function loadJson<T>(url: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export async function getApi<T>(path: string, fallback: T): Promise<T> {
  return loadJson<T>(`/api/v1${path}`, fallback);
}

export const staticDataClient = {
  scrapeSummary: (fallback: ScrapeSummary) => loadJson<ScrapeSummary>("/data/scrape-summary.json", fallback),
  races: () => loadJson<RaceRow[]>("/data/structured-races.json", []),
  entries: () => loadJson<EntryRow[]>("/data/structured-entries.json", []),
  horseHistory: () => loadJson<HorseFormRecord[]>("/data/structured-horse-form-records.json", []),
  changeEvents: () => loadJson<ChangeEventRow[]>("/data/structured-change-events.json", []),
  results: () => loadJson<ResultRow[]>("/data/structured-results.json", []),
  dividends: () => loadJson<DividendRow[]>("/data/structured-dividends.json", []),
  predictions: () => loadJson<PredictionRow[]>("/data/baseline_predictions.json", []),
  jobs: () => loadJson<ScrapeJob[]>("/data/scrape-jobs.json", []),
  backtest: (fallback: BacktestReport) => loadJson<BacktestReport>("/data/backtest_latest.json", fallback),
  oddsChanges: (fallback: OddsChangeReport) => loadJson<OddsChangeReport>("/data/odds_changes.json", fallback),
};

export const apiClient = {
  health: () => loadJson<{ status: string }>("/health", { status: "unknown" }),
  races: () => getApi<{ items: RaceRow[] }>("/racing/races", { items: [] }),
  predictions: () => getApi<{ items: PredictionRow[] }>("/predictions", { items: [] }),
  backtestResults: (runId: number) =>
    getApi<{ run: Record<string, unknown>; bets: BacktestBet[]; equityCurve: BacktestEquityPoint[]; candidateExplanations: BacktestCandidateExplanation[] }>(
      `/backtests/${runId}/results`,
      { run: {}, bets: [], equityCurve: [], candidateExplanations: [] },
    ),
};
