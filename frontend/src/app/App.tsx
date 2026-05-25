import {
  Activity,
  ArrowRight,
  BarChart3,
  Brain,
  ChevronLeft,
  ChevronRight,
  Database,
  Gauge,
  LineChart,
  ListChecks,
  LockKeyhole,
  Mail,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Table2,
  Trophy,
} from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";

type Page = "dashboard" | "data" | "odds" | "model" | "features" | "backtests" | "settings";
type DataCategory = "sources" | "races" | "entries" | "horseHistory" | "changeEvents" | "results" | "dividends" | "jobs";

type RaceDay = { date: string; rows: number };
type SourceRow = {
  id: string;
  category: string;
  source: string;
  title: string;
  recordCount: number;
  updatedAt: string;
};
type ScrapeSummary = {
  generatedAt?: string;
  raceDays: RaceDay[];
  sourceRows: SourceRow[];
};
type RaceRow = {
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
type ResultRow = {
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
type EntryRow = {
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
type HorseFormRecord = {
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
type ChangeEventRow = {
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
type DividendRow = {
  raceDate: string;
  racecourse: string | null;
  raceNo: number;
  pool: string;
  winningCombination: string;
  dividend: string;
};
type PredictionRow = {
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
type ScrapeJob = {
  raceDate: string;
  racecourse: string;
  status: string;
  attempts: number;
  startedAt?: string;
  finishedAt?: string;
  lastError?: string | null;
};
type BacktestMetrics = {
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
type BacktestBet = {
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
type BacktestEquityPoint = {
  sequence: number;
  race_date: string;
  racecourse: string;
  race_no: number;
  bankroll: number;
  drawdown: number;
};
type BacktestReport = {
  config: Record<string, unknown>;
  metrics: BacktestMetrics;
  bets: BacktestBet[];
  equityCurve: BacktestEquityPoint[];
  assumptions: string[];
};
type BacktestFormState = {
  betType: string;
  stakeStrategy: string;
  flatStake: string;
  minEdge: string;
  minProbability: string;
  topN: string;
  startDate: string;
  endDate: string;
};
type OddsPoint = {
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
type OddsSeries = {
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
type OddsChangeReport = {
  raceDate: string;
  raceNo: number;
  oddsType: string;
  series: OddsSeries[];
};

const pageSize = 10;

const fallbackSummary: ScrapeSummary = {
  raceDays: [],
  sourceRows: [],
};
const fallbackBacktest: BacktestReport = {
  config: {},
  metrics: {
    initialBankroll: 0,
    finalBankroll: 0,
    turnover: 0,
    profitLoss: 0,
    roi: null,
    hitRate: null,
    maxDrawdown: 0,
    profitFactor: null,
    averageOdds: null,
    betCount: 0,
  },
  bets: [],
  equityCurve: [],
  assumptions: [],
};
const fallbackOddsChanges: OddsChangeReport = {
  raceDate: "",
  raceNo: 0,
  oddsType: "win",
  series: [],
};

export function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const currentPage = pageFromPath(location.pathname);
  const [summary, setSummary] = useState<ScrapeSummary>(fallbackSummary);
  const [races, setRaces] = useState<RaceRow[]>([]);
  const [entries, setEntries] = useState<EntryRow[]>([]);
  const [horseHistory, setHorseHistory] = useState<HorseFormRecord[]>([]);
  const [changeEvents, setChangeEvents] = useState<ChangeEventRow[]>([]);
  const [results, setResults] = useState<ResultRow[]>([]);
  const [dividends, setDividends] = useState<DividendRow[]>([]);
  const [predictions, setPredictions] = useState<PredictionRow[]>([]);
  const [selectedModelKey, setSelectedModelKey] = useState("all");
  const [jobs, setJobs] = useState<ScrapeJob[]>([]);
  const [backtest, setBacktest] = useState<BacktestReport>(fallbackBacktest);
  const [oddsChanges, setOddsChanges] = useState<OddsChangeReport>(fallbackOddsChanges);

  useEffect(() => {
    loadJson<ScrapeSummary>("/data/scrape-summary.json", fallbackSummary).then(setSummary);
    loadJson<RaceRow[]>("/data/structured-races.json", []).then(setRaces);
    loadJson<EntryRow[]>("/data/structured-entries.json", []).then(setEntries);
    loadJson<HorseFormRecord[]>("/data/structured-horse-form-records.json", []).then(setHorseHistory);
    loadJson<ChangeEventRow[]>("/data/structured-change-events.json", []).then(setChangeEvents);
    loadJson<ResultRow[]>("/data/structured-results.json", []).then(setResults);
    loadJson<DividendRow[]>("/data/structured-dividends.json", []).then(setDividends);
    loadJson<PredictionRow[]>("/data/baseline_predictions.json", []).then(setPredictions);
    loadJson<ScrapeJob[]>("/data/scrape-jobs.json", []).then(setJobs);
    loadJson<BacktestReport>("/data/backtest_latest.json", fallbackBacktest).then(setBacktest);
    loadJson<OddsChangeReport>("/data/odds_changes.json", fallbackOddsChanges).then(setOddsChanges);
  }, []);

  const raceDays = summary.raceDays;
  const latestDate = raceDays[0]?.date ?? races[0]?.raceDate ?? "-";
  const modelOptions = modelVersionOptions(predictions);
  const visiblePredictions = selectedModelKey === "all" ? predictions : predictions.filter((row) => modelKey(row) === selectedModelKey);

  if (location.pathname === "/login") {
    return <LoginPage />;
  }

  return (
    <main className="flex h-screen overflow-hidden bg-canvas text-ink">
      <aside className="flex h-screen w-[300px] shrink-0 flex-col border-r border-hairline-strong bg-canvas">
        <div className="flex h-14 items-center gap-3 border-b border-hairline-strong px-5">
          <RaceQuantLogo />
          <div className="text-lg font-medium tracking-[-0.3px]">赛马量化</div>
        </div>

        <button
          className={[
            "mx-3 mt-4 flex items-center gap-3 rounded-lg border px-3 py-3 text-left text-sm transition-colors",
            currentPage === "dashboard"
              ? "border-hairline-strong bg-surface-elevated text-ink"
              : "border-transparent text-charcoal hover:border-hairline hover:bg-surface-card hover:text-ink",
          ].join(" ")}
          type="button"
          onClick={() => navigate("/")}
        >
          <Gauge className="size-4 text-accent-green" />
          仪表盘
        </button>

        <div className="flex items-center justify-between px-6 pb-3 pt-5">
          <span className="text-sm text-charcoal">赛日</span>
          <Badge>{raceDays.length} days</Badge>
        </div>

        <ScrollArea className="min-h-0 flex-1 px-3 pb-4">
          {raceDays.map((day) => {
            const active = location.pathname === `/race-days/${day.date}`;
            return (
              <button
                key={day.date}
                className={[
                  "mb-2 flex w-full items-center justify-between rounded-lg border px-3 py-3 text-left transition-colors",
                  active
                    ? "border-hairline-strong bg-surface-elevated text-ink"
                    : "border-transparent text-charcoal hover:border-hairline hover:bg-surface-card hover:text-ink",
                ].join(" ")}
                type="button"
                onClick={() => navigate(`/race-days/${day.date}`)}
              >
                <span>
                  <span className="block text-sm font-medium">{day.date}</span>
                  <span className="mt-1 block text-xs text-ash">{formatNumber(day.rows)} 条记录</span>
                </span>
                <LineChart className="size-4 text-accent-blue" />
              </button>
            );
          })}
        </ScrollArea>

        <div className="border-t border-hairline p-4">
          <SettingsMenu currentPage={currentPage} />
        </div>
      </aside>

      <section className="h-screen min-w-0 flex-1 overflow-y-auto">
        <Routes>
          <Route
            path="/"
            element={
              <DashboardPage
                latestDate={latestDate}
                races={races}
                results={results}
                predictions={visiblePredictions}
                jobs={jobs}
              />
            }
          />
          <Route
            path="/race-days/:raceDate"
            element={<RaceDayPage races={races} results={results} dividends={dividends} predictions={visiblePredictions} />}
          />
          <Route path="/data" element={<Navigate replace to="/data/sources" />} />
          <Route
            path="/data/:category"
            element={
              <DataPage
                summary={summary}
                races={races}
                entries={entries}
                horseHistory={horseHistory}
                changeEvents={changeEvents}
                results={results}
                dividends={dividends}
                jobs={jobs}
              />
            }
          />
          <Route path="/odds" element={<OddsPage report={oddsChanges} />} />
          <Route
            path="/model"
            element={
              <PredictionPage
                modelOptions={modelOptions}
                predictions={visiblePredictions}
                selectedModelKey={selectedModelKey}
                onModelChange={setSelectedModelKey}
              />
            }
          />
          <Route path="/features" element={<FeaturePage />} />
          <Route path="/backtests" element={<BacktestPage report={backtest} />} />
          <Route path="/settings" element={<SettingsPage jobs={jobs} />} />
          <Route path="*" element={<Navigate replace to="/" />} />
        </Routes>
      </section>
    </main>
  );
}

/* Hallmark pre-emit critique: P5 H4 E5 S5 R5 V4 */
function LoginPage() {
  const navigate = useNavigate();

  return (
    <main className="relative min-h-screen overflow-x-clip bg-canvas text-ink">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[520px] bg-[radial-gradient(circle_at_52%_0%,rgba(0,117,255,0.34),transparent_62%)]" />
      <div className="relative mx-auto grid min-h-screen max-w-content grid-cols-1 px-5 py-6 lg:grid-cols-[minmax(0,1.05fr)_420px] lg:gap-16 lg:px-8">
        <section className="flex min-h-[42vh] flex-col justify-between border-b border-hairline pb-10 lg:min-h-0 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-16">
          <div className="flex h-14 items-center gap-3">
            <RaceQuantLogo />
            <span className="text-lg font-medium tracking-[-0.3px]">赛马量化</span>
          </div>

          <div className="max-w-[760px] py-12 lg:py-0">
            <Badge>量化工作台</Badge>
            <h1 className="mt-6 max-w-[720px] font-display text-[48px] leading-none tracking-[-0.96px] text-ink sm:text-[64px] lg:text-[88px]">
              用数据进入每一个赛日。
            </h1>
            <p className="mt-6 max-w-[560px] text-lg leading-8 text-body">
              登录后查看赛事元数据、赔率变化、特征工程、模型预测和回测结果。这里不是营销页，是面向赛马量化研究的控制台入口。
            </p>
          </div>

          <div className="grid gap-3 text-sm text-charcoal sm:grid-cols-3">
            <LoginSignal icon={<Activity className="size-4" />} label="采集状态" value="历史赛日回填中" />
            <LoginSignal icon={<BarChart3 className="size-4" />} label="赔率数据" value="win / fct / qin / qpl" />
            <LoginSignal icon={<ShieldCheck className="size-4" />} label="系统边界" value="本地研究环境" />
          </div>
        </section>

        <section className="flex items-center py-10 lg:py-0">
          <Card className="w-full border-hairline-strong bg-surface-card">
            <CardHeader className="p-8 pb-5">
              <CardTitle className="text-2xl tracking-[-0.4px]">登录系统</CardTitle>
              <p className="mt-2 text-sm leading-6 text-charcoal">使用你的本地账号进入量化工作台。</p>
            </CardHeader>
            <CardContent className="p-8 pt-0">
              <form
                className="space-y-5"
                onSubmit={(event) => {
                  event.preventDefault();
                  navigate("/");
                }}
              >
                <label className="block">
                  <span className="mb-2 block text-sm text-charcoal">账号</span>
                  <span className="flex h-11 items-center gap-3 rounded-md border border-hairline-strong bg-surface-deep px-3 focus-within:border-ink">
                    <Mail className="size-4 text-ash" />
                    <input
                      className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-stone"
                      name="account"
                      placeholder="admin@racequant.local"
                      type="email"
                    />
                  </span>
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm text-charcoal">密码</span>
                  <span className="flex h-11 items-center gap-3 rounded-md border border-hairline-strong bg-surface-deep px-3 focus-within:border-ink">
                    <LockKeyhole className="size-4 text-ash" />
                    <input
                      className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-stone"
                      name="password"
                      placeholder="输入密码"
                      type="password"
                    />
                  </span>
                </label>

                <div className="flex items-center justify-between text-sm">
                  <label className="flex items-center gap-2 text-charcoal">
                    <input className="size-4 accent-white" type="checkbox" />
                    保持登录
                  </label>
                  <button className="text-accent-blue hover:text-ink" type="button">
                    忘记密码
                  </button>
                </div>

                <Button className="h-11 w-full justify-between" type="submit">
                  进入工作台
                  <ArrowRight className="size-4" />
                </Button>
              </form>

              <div className="mt-6 rounded-lg border border-hairline bg-surface-deep p-4 text-sm leading-6 text-charcoal">
                <span className="text-ink">提示：</span>
                当前是前端登录样式与路由占位，后续接入真实认证后再替换提交逻辑。
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}

function LoginSignal({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-hairline-strong bg-surface-card p-4">
      <div className="flex items-center gap-2 text-ash">
        <span className="text-accent-green">{icon}</span>
        {label}
      </div>
      <div className="mt-3 text-sm text-ink">{value}</div>
    </div>
  );
}

/* Hallmark pre-emit critique: P5 H5 E5 S5 R5 V4 */
function DashboardPage({
  latestDate,
  races,
  results,
  predictions,
  jobs,
}: {
  latestDate: string;
  races: RaceRow[];
  results: ResultRow[];
  predictions: PredictionRow[];
  jobs: ScrapeJob[];
}) {
  const navigate = useNavigate();
  const latestRaces = races.filter((race) => race.raceDate === latestDate);
  const displayRaces = latestRaces.length > 0 ? latestRaces : races.slice(0, 10);
  const displayRaceDate = latestRaces.length > 0 ? latestDate : displayRaces[0]?.raceDate ?? latestDate;
  const completedJobs = jobs.filter((job) => job.status === "done").length;
  const failedJobs = jobs.filter((job) => job.status === "failed").length;
  const runningJobs = jobs.filter((job) => job.status === "running").length;
  const totalJobs = jobs.length;
  const completionRate = totalJobs > 0 ? Math.round((completedJobs / totalJobs) * 100) : 0;
  const valueBets = predictions.filter((item) => item.isValueBet);
  const topSignal = valueBets[0] ?? predictions[0];

  return (
    <div className="relative min-h-screen overflow-x-clip px-5 py-5">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[520px] bg-[radial-gradient(circle_at_48%_0%,rgba(34,255,153,0.18),transparent_62%)]" />
      <div className="relative mx-auto max-w-content">
        <header className="border-b border-hairline pb-8 pt-2">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <Badge>项目总览</Badge>
            <Button variant="ghost" onClick={() => navigate("/data/results")}>
              查看基础数据
              <ArrowRight className="ml-2 size-4" />
            </Button>
          </div>
          <div className="mt-8 grid gap-8 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div>
              <h1 className="max-w-[780px] font-display text-[52px] leading-none tracking-[-0.96px] sm:text-[72px] lg:text-[88px]">
                赛日、赔率、模型在同一张桌面上。
              </h1>
              <p className="mt-6 max-w-[640px] text-lg leading-8 text-body">
                这里先回答今天系统是否有数据、历史回填跑到哪里、baseline 是否已经产出信号。细节再进入赛日、数据、模型和回测页面。
              </p>
            </div>
            <div className="rounded-lg border border-hairline-strong bg-surface-card p-6">
              <div className="text-sm text-charcoal">最新赛日</div>
              <div className="mt-3 font-display text-5xl leading-none tracking-[-0.96px]">{latestDate}</div>
              <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
                <StatusPill label="赛事元数据" value={`${latestRaces.length} 场`} />
                <StatusPill label="赛果记录" value={`${formatNumber(results.length)} 条`} />
              </div>
            </div>
          </div>
        </header>

        <section className="grid gap-4 py-5 md:grid-cols-2 xl:grid-cols-4">
          <DashboardMetric icon={<Database className="size-4" />} title="结构化赛果" value={formatNumber(results.length)} note="runner 级记录" />
          <DashboardMetric icon={<Activity className="size-4" />} title="历史回填" value={`${completionRate}%`} note={`${completedJobs} / ${totalJobs} 个赛日任务`} />
          <DashboardMetric icon={<Brain className="size-4" />} title="模型输出" value={formatNumber(predictions.length)} note={predictions[0]?.modelVersion ?? "等待生成"} />
          <DashboardMetric icon={<Sparkles className="size-4" />} title="价值信号" value={String(valueBets.length)} note="当前 baseline 规则" />
        </section>

        <section className="grid gap-5 pb-8 xl:grid-cols-[minmax(0,1.25fr)_420px]">
          <Card className="bg-surface-card">
            <CardHeader className="flex flex-row items-start justify-between gap-4 p-6 pb-2">
              <div>
                <CardTitle>{latestRaces.length > 0 ? "最新赛事" : `最近赛事 ${displayRaceDate}`}</CardTitle>
                <p className="mt-1 text-sm text-charcoal">按场次快速扫描距离、班次、场地和赛事名称。</p>
              </div>
              <Trophy className="mt-1 size-5 shrink-0 text-accent-yellow" />
            </CardHeader>
            <CardContent className="p-6 pt-3">
              <CompactRaceList rows={displayRaces} />
            </CardContent>
          </Card>

          <div className="space-y-5">
            <Card className="bg-surface-elevated">
              <CardHeader className="p-6 pb-2">
                <CardTitle>模型信号</CardTitle>
                <p className="mt-1 text-sm text-charcoal">只展示已生成的 baseline 输出，不展示模拟指标。</p>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                {topSignal ? (
                  <div>
                    <div className="rounded-lg border border-hairline bg-surface-deep p-4">
                      <div className="text-sm text-charcoal">{topSignal.raceDate} · {topSignal.racecourse} R{topSignal.raceNo}</div>
                      <div className="mt-2 text-xl font-medium text-ink">{topSignal.horseNo}. {topSignal.horseName}</div>
                      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                        <StatusPill label="胜率" value={percent(topSignal.winProbability)} />
                        <StatusPill label="Edge" value={topSignal.edge == null ? "-" : percent(topSignal.edge)} />
                      </div>
                    </div>
                    <div className="mt-4 space-y-2 text-sm">
                      <StatusLine label="模型" value={topSignal.modelName} />
                      <StatusLine label="版本" value={topSignal.modelVersion} />
                      <StatusLine label="预测样本" value={`${predictions.length} 条`} />
                      <StatusLine label="价值投注" value={`${valueBets.length} 条`} />
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-charcoal">暂无模型预测。生成 baseline 输出后这里会显示首个信号。</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-6 pb-2">
                <CardTitle>采集进度</CardTitle>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <ProgressTrack value={completionRate} />
                <div className="mt-5 grid grid-cols-3 gap-3 text-sm">
                  <StatusPill label="完成" value={String(completedJobs)} />
                  <StatusPill label="运行" value={String(runningJobs)} />
                  <StatusPill label="失败" value={String(failedJobs)} />
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}

/* Hallmark pre-emit critique: P5 H5 E5 S5 R5 V5 */
function RaceDayPage({
  races,
  results,
  dividends,
  predictions,
}: {
  races: RaceRow[];
  results: ResultRow[];
  dividends: DividendRow[];
  predictions: PredictionRow[];
}) {
  const { raceDate = "" } = useParams();
  const dayRaces = races.filter((race) => race.raceDate === raceDate);
  const dayResults = results.filter((row) => row.raceDate === raceDate);
  const dayDividends = dividends.filter((row) => row.raceDate === raceDate);
  const dayPredictions = predictions.filter((row) => row.raceDate === raceDate);
  const raceNos = Array.from(new Set([...dayRaces.map((race) => race.raceNo), ...dayResults.map((row) => row.raceNo), ...dayPredictions.map((row) => row.raceNo)])).sort((a, b) => a - b);
  const raceNoKey = raceNos.join(",");
  const [selectedRaceNo, setSelectedRaceNo] = useState<number | null>(null);
  const activeRaceNo = selectedRaceNo && raceNos.includes(selectedRaceNo) ? selectedRaceNo : raceNos[0] ?? 1;
  const activeRace = dayRaces.find((race) => race.raceNo === activeRaceNo);
  const raceResults = dayResults.filter((row) => row.raceNo === activeRaceNo);
  const raceDividends = dayDividends.filter((row) => row.raceNo === activeRaceNo);
  const racePredictions = dayPredictions.filter((row) => row.raceNo === activeRaceNo);
  const rankedPredictions = [...racePredictions].sort((a, b) => (b.edge ?? b.winProbability) - (a.edge ?? a.winProbability));
  const valueBets = rankedPredictions.filter((row) => row.isValueBet || (row.edge ?? 0) > 0);
  const primaryPick = valueBets[0] ?? rankedPredictions[0];
  const placePicks = [...racePredictions].sort((a, b) => b.placeProbability - a.placeProbability).slice(0, 3);
  const quinellaPicks = [...racePredictions].sort((a, b) => b.winProbability - a.winProbability).slice(0, 2);

  useEffect(() => {
    if (raceNos.length > 0 && !raceNos.includes(activeRaceNo)) {
      setSelectedRaceNo(raceNos[0]);
    }
  }, [activeRaceNo, raceNoKey, raceNos]);

  return (
    <div className="relative min-h-screen overflow-x-clip px-5 py-5">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[460px] bg-[radial-gradient(circle_at_48%_0%,rgba(0,117,255,0.34),transparent_62%)]" />
      <div className="relative mx-auto max-w-content">
        <header className="border-b border-hairline pb-6">
          <Badge>赛日详情</Badge>
          <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div>
              <h1 className="font-display text-[48px] leading-none tracking-[-0.96px] sm:text-[64px] lg:text-[76px]">
                {raceDate}
              </h1>
              <p className="mt-4 max-w-[680px] text-lg leading-8 text-body">
                先选场次，再看模型、信号、策略和组合。这里聚焦投注决策，不把基础数据表铺满首屏。
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <StatusPill label="场次数" value={`${raceNos.length} 场`} />
              <StatusPill label="参赛记录" value={`${formatNumber(dayResults.length)} 条`} />
              <StatusPill label="派彩记录" value={`${formatNumber(dayDividends.length)} 条`} />
              <StatusPill label="模型输出" value={`${formatNumber(dayPredictions.length)} 条`} />
            </div>
          </div>
        </header>

        <RaceTabs raceNos={raceNos} activeRaceNo={activeRaceNo} onChange={setSelectedRaceNo} />

        <section className="grid gap-5 pb-8 xl:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-5">
            <Card className="bg-surface-card">
              <CardHeader className="p-6 pb-2">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <CardTitle>第 {activeRaceNo} 场 · {activeRace?.raceName ?? "赛事待解析"}</CardTitle>
                    <p className="mt-1 text-sm text-charcoal">
                      {[activeRace?.racecourse, activeRace?.raceClass, activeRace?.distanceM ? `${activeRace.distanceM}m` : null, activeRace?.going].filter(Boolean).join(" · ") || "暂无赛事元数据"}
                    </p>
                  </div>
                  <Badge>{activeRace?.raceIndex ? `Race ${activeRace.raceIndex}` : `R${activeRaceNo}`}</Badge>
                </div>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <div className="grid gap-3 md:grid-cols-4">
                  <StatusPill label="奖金" value={activeRace?.prizeMoney ?? "-"} />
                  <StatusPill label="跑道" value={[activeRace?.surface, activeRace?.courseLayout].filter(Boolean).join(" / ") || "-"} />
                  <StatusPill label="参赛马" value={`${raceResults.length} 匹`} />
                  <StatusPill label="派彩" value={`${raceDividends.length} 条`} />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-6 pb-2">
                <CardTitle>推荐投注策略</CardTitle>
                <p className="mt-1 text-sm text-charcoal">以当前模型输出为候选，不替代正式下注前的盘口和风控确认。</p>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <div className="grid gap-3 md:grid-cols-3">
                  <StrategyCard
                    title="独赢候选"
                    value={primaryPick ? `${primaryPick.horseNo}. ${primaryPick.horseName}` : "暂无"}
                    note={primaryPick ? `胜率 ${percent(primaryPick.winProbability)} · Edge ${primaryPick.edge == null ? "-" : percent(primaryPick.edge)}` : "等待模型输出"}
                  />
                  <StrategyCard
                    title="位置候选"
                    value={placePicks.length ? placePicks.map((pick) => pick.horseNo).join(" / ") : "暂无"}
                    note={placePicks.length ? placePicks.map((pick) => `${pick.horseNo} ${percent(pick.placeProbability)}`).join(" · ") : "等待模型输出"}
                  />
                  <StrategyCard
                    title="连赢组合"
                    value={quinellaPicks.length >= 2 ? quinellaPicks.map((pick) => pick.horseNo).join(" - ") : "暂无"}
                    note={quinellaPicks.length >= 2 ? "按胜率排序的双马组合候选" : "需要至少两匹预测马"}
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="overflow-hidden">
              <CardHeader className="p-6 pb-2">
                <CardTitle>参赛马与模型排序</CardTitle>
              </CardHeader>
              <RaceRunnerTable results={raceResults} predictions={rankedPredictions} />
            </Card>
          </div>

          <div className="space-y-5">
            <Card className="bg-surface-elevated">
              <CardHeader className="p-6 pb-2">
                <CardTitle>模型状态</CardTitle>
                <p className="mt-1 text-sm text-charcoal">准确率和 ROI 需要接入按模型版本的回测结果。</p>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <div className="space-y-2 text-sm">
                  <StatusLine label="使用模型" value={racePredictions[0]?.modelName ?? "未生成预测"} />
                  <StatusLine label="模型版本" value={racePredictions[0]?.modelVersion ?? "待生成"} />
                  <StatusLine label="准确率" value="待回测接入" />
                  <StatusLine label="模型 ROI" value="待回测接入" />
                  <StatusLine label="本场预测" value={`${racePredictions.length} 条`} />
                  <StatusLine label="价值候选" value={`${valueBets.length} 条`} />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-6 pb-2">
                <CardTitle>推荐投注组合</CardTitle>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <BetCombinationList primaryPick={primaryPick} placePicks={placePicks} quinellaPicks={quinellaPicks} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-6 pb-2">
                <CardTitle>派彩参考</CardTitle>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <DividendSummary rows={raceDividends} />
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}

function DataPage({
  summary,
  races,
  entries,
  horseHistory,
  changeEvents,
  results,
  dividends,
  jobs,
}: {
  summary: ScrapeSummary;
  races: RaceRow[];
  entries: EntryRow[];
  horseHistory: HorseFormRecord[];
  changeEvents: ChangeEventRow[];
  results: ResultRow[];
  dividends: DividendRow[];
  jobs: ScrapeJob[];
}) {
  const { category } = useParams();
  const current = isDataCategory(category) ? category : "sources";
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const tabs: Array<{ label: string; value: DataCategory }> = [
    { label: "数据源", value: "sources" },
    { label: "赛事", value: "races" },
    { label: "参赛排位", value: "entries" },
    { label: "马匹历史", value: "horseHistory" },
    { label: "临场变更", value: "changeEvents" },
    { label: "赛果", value: "results" },
    { label: "派彩", value: "dividends" },
    { label: "采集任务", value: "jobs" },
  ];
  const discoveredHorseCodes = new Set(
    [...entries.map((row) => row.horseCode), ...results.map((row) => row.horseCode)].filter(Boolean),
  );
  const coveredHorseCodes = new Set(horseHistory.map((row) => row.horseCode).filter(Boolean));
  const horseHistoryCoverage =
    discoveredHorseCodes.size > 0 ? Math.round((coveredHorseCodes.size / discoveredHorseCodes.size) * 100) : 0;
  const statusCounts = jobStatusCounts(jobs);
  const activeJobs = statusCounts.pending + statusCounts.running + statusCounts.failed;
  const totalOfficialJobs = statusCounts.done + activeJobs;
  const completionRate = totalOfficialJobs > 0 ? Math.round((statusCounts.done / totalOfficialJobs) * 100) : 0;

  return (
    <div className="min-h-screen">
      <header className="flex h-14 items-center justify-between border-b border-hairline-strong px-5">
        <nav className="flex min-w-0 gap-2 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.value}
              className={[
                "h-9 whitespace-nowrap rounded-full px-4 text-sm transition-colors",
                current === tab.value
                  ? "bg-primary text-primary-on"
                  : "border border-hairline-strong bg-surface-card text-charcoal hover:text-ink",
              ].join(" ")}
              type="button"
              onClick={() => {
                setPage(1);
                navigate(`/data/${tab.value}`);
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        <Button variant="ghost">
          <Table2 className="mr-2 size-4" />
          基础数据
        </Button>
      </header>
      <div className="px-5 py-5">
        <DataCompletenessPanel
          activeCategory={current}
          horseHistoryCoverage={horseHistoryCoverage}
          discoveredHorseCount={discoveredHorseCodes.size}
          coveredHorseCount={coveredHorseCodes.size}
          activeJobs={activeJobs}
          doneJobs={statusCounts.done}
          skippedJobs={statusCounts.skipped}
          completionRate={completionRate}
        />
        {current === "sources" && <SourceTable rows={summary.sourceRows} page={page} onPageChange={setPage} />}
        {current === "races" && <RaceTable rows={races} page={page} onPageChange={setPage} />}
        {current === "entries" && <EntryTable rows={entries} page={page} onPageChange={setPage} />}
        {current === "horseHistory" && <HorseHistoryTable rows={horseHistory} page={page} onPageChange={setPage} />}
        {current === "changeEvents" && <ChangeEventTable rows={changeEvents} page={page} onPageChange={setPage} />}
        {current === "results" && <ResultTable rows={results} page={page} onPageChange={setPage} />}
        {current === "dividends" && <DividendTable rows={dividends} page={page} onPageChange={setPage} />}
        {current === "jobs" && <JobTable rows={jobs} page={page} onPageChange={setPage} />}
      </div>
    </div>
  );
}

function PredictionPage({
  predictions,
  modelOptions,
  selectedModelKey,
  onModelChange,
}: {
  predictions: PredictionRow[];
  modelOptions: Array<{ key: string; label: string }>;
  selectedModelKey: string;
  onModelChange: (key: string) => void;
}) {
  const [page, setPage] = useState(1);
  const valueCount = predictions.filter((item) => item.isValueBet).length;
  const meta = modelMetadata(predictions);
  const probabilityRows = [...predictions]
    .sort((left, right) => right.winProbability - left.winProbability)
    .slice(0, 12);
  const adviceRows = [...predictions]
    .filter((item) => item.isValueBet || (item.edge ?? 0) > 0)
    .sort((left, right) => (right.edge ?? -1) - (left.edge ?? -1))
    .slice(0, 12);
  return (
    <PageShell title="预测看板" eyebrow="Model">
      <div className="grid gap-4 lg:grid-cols-3">
        <MetricCard title="预测记录" value={formatNumber(predictions.length)} note="当前 baseline 输出" />
        <MetricCard title="价值投注" value={String(valueCount)} note="edge >= 3%" />
        <MetricCard title="模型版本" value={predictions[0]?.modelVersion ?? "-"} note={predictions[0]?.modelName ?? "未生成"} />
      </div>
      <div className="mt-5 flex justify-end">
        <ModelVersionMenu options={modelOptions} selectedKey={selectedModelKey} onSelect={onModelChange} />
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatusPill label="赔率模式" value={meta.oddsMode} />
        <StatusPill label="训练数据" value={meta.trainingDatasetVersion} />
        <StatusPill label="特征版本" value={meta.featureVersion} />
        <StatusPill label="数据构建" value={meta.dataBuildId} />
      </div>
      {meta.isLeakageRisk && (
        <div className="mt-5">
          <RiskNotice />
        </div>
      )}
      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader className="p-6 pb-2">
            <CardTitle>概率预测</CardTitle>
            <p className="mt-1 text-sm text-charcoal">只展示模型胜率和位置概率，不包含下注资金建议。</p>
          </CardHeader>
          <ProbabilityPredictionTable rows={probabilityRows} />
        </Card>
        <Card className="overflow-hidden">
          <CardHeader className="p-6 pb-2">
            <CardTitle>下注建议</CardTitle>
            <p className="mt-1 text-sm text-charcoal">按 edge 和候选状态筛选，保持预测与资金管理边界清晰。</p>
          </CardHeader>
          <BettingAdviceTable rows={adviceRows} />
        </Card>
      </div>
      <div className="mt-5">
        <PredictionTable rows={predictions} page={page} onPageChange={setPage} />
      </div>
    </PageShell>
  );
}

function OddsPage({ report }: { report: OddsChangeReport }) {
  const [selectedValue, setSelectedValue] = useState<string | null>(null);
  const activeSeries = report.series.find((item) => item.oddsValue === selectedValue) ?? report.series[0];
  const totalSnapshots = report.series.reduce((sum, item) => sum + item.snapshotCount, 0);

  return (
    <div className="relative min-h-screen overflow-x-clip px-5 py-5">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[460px] bg-[radial-gradient(circle_at_48%_0%,rgba(0,117,255,0.34),transparent_62%)]" />
      <div className="relative mx-auto max-w-content">
        <header className="border-b border-hairline pb-8 pt-2">
          <Badge>赔率变化</Badge>
          <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div>
              <h1 className="font-display text-[52px] leading-none tracking-[-0.96px] sm:text-[72px] lg:text-[88px]">
                盘口移动，比结果更早说话。
              </h1>
              <p className="mt-5 max-w-[660px] text-lg leading-8 text-body">
                展示已迁移旧库中的历史赔率变化。完整历史赔率库已后置，当前可用范围为 {report.raceDate || "-"} 第 {report.raceNo || "-"} 场 {report.oddsType.toUpperCase()}。
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <StatusPill label="赔率对象" value={`${report.series.length} 个`} />
              <StatusPill label="快照" value={`${formatNumber(totalSnapshots)} 条`} />
              <StatusPill label="赛日" value={report.raceDate || "-"} />
              <StatusPill label="场次" value={report.raceNo ? `R${report.raceNo}` : "-"} />
            </div>
          </div>
        </header>

        <section className="grid gap-5 py-5 xl:grid-cols-[minmax(0,1.1fr)_420px]">
          <Card className="overflow-hidden">
            <CardHeader className="p-6 pb-2">
              <CardTitle>赔率变化列表</CardTitle>
              <p className="mt-1 text-sm text-charcoal">点击一行查看右侧曲线。</p>
            </CardHeader>
            <OddsChangeTable rows={report.series} activeValue={activeSeries?.oddsValue ?? ""} onSelect={setSelectedValue} />
          </Card>

          <div className="space-y-5">
            <Card className="bg-surface-elevated">
              <CardHeader className="p-6 pb-2">
                <CardTitle>{activeSeries ? `${activeSeries.oddsValue} 号赔率曲线` : "赔率曲线"}</CardTitle>
                <p className="mt-1 text-sm text-charcoal">按快照时间从左到右。</p>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <OddsSparkline series={activeSeries} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-6 pb-2">
                <CardTitle>快照明细</CardTitle>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <OddsSnapshotList points={activeSeries?.points ?? []} />
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}

function FeaturePage() {
  return (
    <PageShell title="特征工程" eyebrow="Features">
      <div className="grid gap-4 lg:grid-cols-3">
        <FeatureCard title="近期表现" items={["近 3 场胜率/位置率", "近 5 场平均名次", "休赛天数"]} />
        <FeatureCard title="赛事适应" items={["距离适应", "场地/地况适应", "升降班"]} />
        <FeatureCard title="市场信息" items={["独赢隐含概率", "模型公允赔率", "value betting edge"]} />
      </div>
    </PageShell>
  );
}

function BacktestPage({ report }: { report: BacktestReport }) {
  const { metrics } = report;
  const config = report.config;
  const oddsMode = stringConfig(config, "odds_mode") || stringConfig(config, "oddsMode") || "-";
  const isLeakageRisk = oddsMode === "result_final";
  const [draftConfig, setDraftConfig] = useState(() => backtestFormFromConfig(config));
  const updateDraftConfig = (field: keyof BacktestFormState, value: string) => {
    setDraftConfig((current) => ({ ...current, [field]: value }));
  };
  return (
    <div className="relative min-h-screen overflow-x-clip px-5 py-5">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[460px] bg-[radial-gradient(circle_at_48%_0%,rgba(255,89,0,0.22),transparent_62%)]" />
      <div className="relative mx-auto max-w-content">
        <header className="border-b border-hairline pb-8 pt-2">
          <Badge>回测系统</Badge>
          <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div>
              <h1 className="font-display text-[52px] leading-none tracking-[-0.96px] sm:text-[72px] lg:text-[88px]">
                资金曲线先说话。
              </h1>
              <p className="mt-5 max-w-[660px] text-lg leading-8 text-body">
                展示阶段 7 回测引擎生成的真实结果：ROI、命中率、最大回撤、资金曲线和投注明细。当前报告来自本地最新导出文件。
              </p>
            </div>
            <div className="rounded-lg border border-hairline-strong bg-surface-card p-5">
              <div className="text-sm text-charcoal">策略配置</div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <StatusPill label="投注类型" value={String(report.config.bet_type ?? "-")} />
                <StatusPill label="注码策略" value={String(report.config.stake_strategy ?? "-")} />
                <StatusPill label="单注" value={money(Number(report.config.flat_stake ?? 0))} />
                <StatusPill label="候选数" value={String(report.config.top_n_per_race ?? "-")} />
                <StatusPill label="赔率模式" value={oddsMode} />
                <StatusPill label="回测版本" value={stringConfig(config, "backtest_version") || stringConfig(config, "backtestVersion") || "-"} />
              </div>
            </div>
          </div>
        </header>

        <section className="grid gap-4 py-5 md:grid-cols-2 xl:grid-cols-4">
          <DashboardMetric icon={<BarChart3 className="size-4" />} title="ROI" value={metrics.roi == null ? "-" : percent(metrics.roi)} note={`盈亏 ${money(metrics.profitLoss)}`} />
          <DashboardMetric icon={<Trophy className="size-4" />} title="命中率" value={metrics.hitRate == null ? "-" : percent(metrics.hitRate)} note={`${metrics.betCount} 笔投注`} />
          <DashboardMetric icon={<LineChart className="size-4" />} title="最大回撤" value={percent(metrics.maxDrawdown)} note={`最终资金 ${money(metrics.finalBankroll)}`} />
          <DashboardMetric icon={<Gauge className="size-4" />} title="平均赔率" value={metrics.averageOdds == null ? "-" : number(metrics.averageOdds)} note={`总投注 ${money(metrics.turnover)}`} />
        </section>

        <section className="grid gap-5 pb-8 xl:grid-cols-[minmax(0,1.15fr)_420px]">
          <div className="space-y-5">
            <BacktestParameterPanel config={draftConfig} onChange={updateDraftConfig} />
            <Card>
              <CardHeader className="p-6 pb-2">
                <CardTitle>资金曲线</CardTitle>
                <p className="mt-1 text-sm text-charcoal">按投注顺序展示 bankroll，非图表封装前先用条形轨迹表达。</p>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <EquityCurve points={report.equityCurve} initialBankroll={metrics.initialBankroll} />
              </CardContent>
            </Card>

            <Card className="overflow-hidden">
              <CardHeader className="p-6 pb-2">
                <CardTitle>投注明细</CardTitle>
              </CardHeader>
              <BacktestBetTable rows={report.bets} />
            </Card>
          </div>

          <div className="space-y-5">
            <Card className="bg-surface-elevated">
              <CardHeader className="p-6 pb-2">
                <CardTitle>结果摘要</CardTitle>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <div className="space-y-2 text-sm">
                  <StatusLine label="初始资金" value={money(metrics.initialBankroll)} />
                  <StatusLine label="最终资金" value={money(metrics.finalBankroll)} />
                  <StatusLine label="总投注额" value={money(metrics.turnover)} />
                  <StatusLine label="盈亏因子" value={metrics.profitFactor == null ? "-" : number(metrics.profitFactor)} />
                  <StatusLine label="模型版本" value={stringConfig(config, "model_version") || stringConfig(config, "modelVersion") || "-"} />
                  <StatusLine label="训练数据" value={stringConfig(config, "training_dataset_version") || stringConfig(config, "trainingDatasetVersion") || "-"} />
                  <StatusLine label="特征版本" value={stringConfig(config, "feature_version") || stringConfig(config, "featureVersion") || "-"} />
                  <StatusLine label="数据构建" value={stringConfig(config, "data_build_id") || stringConfig(config, "dataBuildId") || "-"} />
                </div>
                {isLeakageRisk && <RiskNotice />}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-6 pb-2">
                <CardTitle>回测假设</CardTitle>
              </CardHeader>
              <CardContent className="p-6 pt-3">
                <div className="space-y-3">
                  {report.assumptions.length ? report.assumptions.map((assumption) => (
                    <div key={assumption} className="flex gap-3 text-sm leading-6 text-body">
                      <ListChecks className="mt-1 size-4 shrink-0 text-accent-green" />
                      {assumption}
                    </div>
                  )) : <p className="text-sm text-charcoal">暂无回测假设。</p>}
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}

function SettingsPage({ jobs }: { jobs: ScrapeJob[] }) {
  const counts = groupCount(jobs.map((job) => job.status));
  return (
    <PageShell title="设置" eyebrow="Pipeline">
      <div className="grid gap-4 lg:grid-cols-3">
        <MetricCard title="Done" value={String(counts.done ?? 0)} note="已完成采集任务" />
        <MetricCard title="Running" value={String(counts.running ?? 0)} note="正在执行" />
        <MetricCard title="Pending" value={String(counts.pending ?? 0)} note="等待采集" />
      </div>
    </PageShell>
  );
}

function SettingsMenu({ currentPage }: { currentPage: Page }) {
  const navigate = useNavigate();
  const items: Array<{ label: string; page: Page; path: string; icon: typeof Database }> = [
    { label: "数据", page: "data", path: "/data/sources", icon: Database },
    { label: "赔率", page: "odds", path: "/odds", icon: LineChart },
    { label: "模型", page: "model", path: "/model", icon: Brain },
    { label: "特征", page: "features", path: "/features", icon: Sparkles },
    { label: "回测", page: "backtests", path: "/backtests", icon: BarChart3 },
    { label: "设置", page: "settings", path: "/settings", icon: SlidersHorizontal },
  ];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button className="w-full justify-start gap-2" variant="ghost">
          <Settings className="size-4" />
          设置
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[268px]" side="top">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <DropdownMenuItem
              key={item.page}
              className={currentPage === item.page ? "bg-surface-card text-ink" : undefined}
              onClick={() => navigate(item.path)}
            >
              <Icon className="size-4 text-accent-blue" />
              {item.label}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function SourceTable({ rows, page, onPageChange }: { rows: SourceRow[]; page: number; onPageChange: (page: number) => void }) {
  const data = paged(rows, page);
  return (
    <DataCard footer={<Pagination page={data.safePage} totalPages={data.totalPages} totalRows={rows.length} onPageChange={onPageChange} />}>
      <TableHeader headers={["类别", "来源", "标题", "记录数", "更新时间"]} />
      <tbody>
        {data.rows.map((row) => (
          <tr key={row.id} className="border-b border-hairline text-body last:border-0">
            <td className="px-5 py-4"><Badge>{row.category}</Badge></td>
            <td className="px-5 py-4 text-ink">{row.source}</td>
            <td className="px-5 py-4 text-charcoal">{row.title}</td>
            <td className="px-5 py-4 text-ink">{row.recordCount}</td>
            <td className="px-5 py-4 text-charcoal">{row.updatedAt}</td>
          </tr>
        ))}
      </tbody>
    </DataCard>
  );
}

function RaceTable({ rows, page = 1, onPageChange }: { rows: RaceRow[]; page?: number; onPageChange?: (page: number) => void }) {
  const data = paged(rows, page);
  return (
    <DataCard footer={onPageChange ? <Pagination page={data.safePage} totalPages={data.totalPages} totalRows={rows.length} onPageChange={onPageChange} /> : null}>
      <TableHeader headers={["赛日", "马场", "场次", "赛事", "班次", "途程", "地况", "跑道"]} />
      <tbody>
        {data.rows.map((row) => (
          <tr key={`${row.raceDate}-${row.racecourse}-${row.raceNo}`} className="border-b border-hairline text-body last:border-0">
            <td className="px-5 py-4 text-ink">{row.raceDate}</td>
            <td className="px-5 py-4">{row.racecourse}</td>
            <td className="px-5 py-4">R{row.raceNo}</td>
            <td className="px-5 py-4 text-ink">{row.raceName ?? "-"}</td>
            <td className="px-5 py-4">{row.raceClass ?? "-"}</td>
            <td className="px-5 py-4">{row.distanceM ? `${row.distanceM}m` : "-"}</td>
            <td className="px-5 py-4">{row.going ?? "-"}</td>
            <td className="px-5 py-4">{[row.surface, row.courseLayout].filter(Boolean).join(" / ") || "-"}</td>
          </tr>
        ))}
      </tbody>
    </DataCard>
  );
}

function ResultTable({ rows, page, onPageChange }: { rows: ResultRow[]; page: number; onPageChange: (page: number) => void }) {
  const data = paged(rows, page);
  return (
    <DataCard footer={<Pagination page={data.safePage} totalPages={data.totalPages} totalRows={rows.length} onPageChange={onPageChange} />}>
      <TableHeader headers={["赛日", "马场", "场次", "名次", "马号", "马匹", "骑师", "练马师", "档位", "时间", "独赢"]} />
      <tbody>
        {data.rows.map((row) => (
          <tr key={`${row.raceDate}-${row.racecourse}-${row.raceNo}-${row.place}-${row.horseNo}`} className="border-b border-hairline text-body last:border-0">
            <td className="px-5 py-4 text-ink">{row.raceDate}</td>
            <td className="px-5 py-4">{row.racecourse}</td>
            <td className="px-5 py-4">R{row.raceNo}</td>
            <td className="px-5 py-4">{row.place}</td>
            <td className="px-5 py-4">{row.horseNo}</td>
            <td className="px-5 py-4 text-ink">{row.horseName}{row.horseCode ? ` (${row.horseCode})` : ""}</td>
            <td className="px-5 py-4">{row.jockey}</td>
            <td className="px-5 py-4">{row.trainer}</td>
            <td className="px-5 py-4">{row.draw}</td>
            <td className="px-5 py-4">{row.finishTime}</td>
            <td className="px-5 py-4 text-ink">{row.winOdds}</td>
          </tr>
        ))}
      </tbody>
    </DataCard>
  );
}

function EntryTable({ rows, page, onPageChange }: { rows: EntryRow[]; page: number; onPageChange: (page: number) => void }) {
  const data = paged(rows, page);
  return (
    <DataCard footer={<Pagination page={data.safePage} totalPages={data.totalPages} totalRows={rows.length} onPageChange={onPageChange} />}>
      <TableHeader headers={["赛日", "马场", "场次", "马号", "马匹", "骑师", "练马师", "档位", "负磅", "评分", "近绩", "配备"]} />
      <tbody>
        {data.rows.map((row) => (
          <tr key={`${row.raceDate}-${row.racecourse}-${row.raceNo}-${row.standby}-${row.horseNo}`} className="border-b border-hairline text-body last:border-0">
            <td className="px-5 py-4 text-ink">{row.raceDate}</td>
            <td className="px-5 py-4">{row.racecourse}</td>
            <td className="px-5 py-4">R{row.raceNo}</td>
            <td className="px-5 py-4">{row.horseNo}</td>
            <td className="px-5 py-4 text-ink">
              {row.horseName}{row.horseCode ? ` (${row.horseCode})` : ""}{row.standby ? " · 候补" : ""}
            </td>
            <td className="px-5 py-4">{row.jockey ?? "-"}</td>
            <td className="px-5 py-4">{row.trainer ?? "-"}</td>
            <td className="px-5 py-4">{row.draw ?? "-"}</td>
            <td className="px-5 py-4">{row.actualWeight ?? "-"}</td>
            <td className="px-5 py-4">{row.rating ?? "-"}</td>
            <td className="px-5 py-4">{row.last6Runs ?? "-"}</td>
            <td className="px-5 py-4">{row.gear ?? "-"}</td>
          </tr>
        ))}
      </tbody>
    </DataCard>
  );
}

function HorseHistoryTable({ rows, page, onPageChange }: { rows: HorseFormRecord[]; page: number; onPageChange: (page: number) => void }) {
  const data = paged(rows, page);
  return (
    <DataCard footer={<Pagination page={data.safePage} totalPages={data.totalPages} totalRows={rows.length} onPageChange={onPageChange} />}>
      <TableHeader headers={["马匹", "赛日", "场地", "途程", "名次", "评分", "骑师", "练马师", "档位", "独赢", "完成时间", "配备"]} />
      <tbody>
        {data.rows.map((row) => (
          <tr key={`${row.horseCode}-${row.raceIndex}`} className="border-b border-hairline text-body last:border-0">
            <td className="px-5 py-4 text-ink">{row.horseCode}</td>
            <td className="px-5 py-4">{row.raceDate ?? "-"}</td>
            <td className="px-5 py-4">{[row.racecourse, row.track, row.course].filter(Boolean).join(" / ") || "-"}</td>
            <td className="px-5 py-4">{row.distanceM ? `${row.distanceM}m` : "-"}</td>
            <td className="px-5 py-4 text-ink">{row.place ?? "-"}</td>
            <td className="px-5 py-4">{row.rating ?? "-"}</td>
            <td className="px-5 py-4">{row.jockey ?? "-"}</td>
            <td className="px-5 py-4">{row.trainer ?? "-"}</td>
            <td className="px-5 py-4">{row.draw ?? "-"}</td>
            <td className="px-5 py-4">{row.winOdds ?? "-"}</td>
            <td className="px-5 py-4">{row.finishTime ?? "-"}</td>
            <td className="px-5 py-4">{row.gear ?? "-"}</td>
          </tr>
        ))}
      </tbody>
    </DataCard>
  );
}

function ChangeEventTable({ rows, page, onPageChange }: { rows: ChangeEventRow[]; page: number; onPageChange: (page: number) => void }) {
  const data = paged(rows, page);
  return (
    <DataCard footer={<Pagination page={data.safePage} totalPages={data.totalPages} totalRows={rows.length} onPageChange={onPageChange} />}>
      <TableHeader headers={["赛日", "场次", "类型", "马号", "马匹", "关联", "骑师", "负磅", "时间", "描述"]} />
      <tbody>
        {data.rows.map((row) => (
          <tr key={`${row.raceDate}-${row.raceNo}-${row.sequence}`} className="border-b border-hairline text-body last:border-0">
            <td className="px-5 py-4 text-ink">{row.raceDate}</td>
            <td className="px-5 py-4">R{row.raceNo}</td>
            <td className="px-5 py-4"><Badge>{changeEventLabel(row.eventType)}</Badge></td>
            <td className="px-5 py-4">{row.horseNo ?? "-"}</td>
            <td className="px-5 py-4 text-ink">{row.horseName ?? "-"}</td>
            <td className="px-5 py-4">{row.relatedHorseName ?? "-"}</td>
            <td className="px-5 py-4">{row.jockey ?? "-"}</td>
            <td className="px-5 py-4">{row.declaredWeight ? `${row.declaredWeight} lbs` : "-"}</td>
            <td className="px-5 py-4 text-charcoal">{row.eventTimeText ?? "-"}</td>
            <td className="max-w-[520px] px-5 py-4 text-charcoal">{row.description}</td>
          </tr>
        ))}
      </tbody>
    </DataCard>
  );
}

function DividendTable({ rows, page, onPageChange }: { rows: DividendRow[]; page: number; onPageChange: (page: number) => void }) {
  const data = paged(rows, page);
  return (
    <DataCard footer={<Pagination page={data.safePage} totalPages={data.totalPages} totalRows={rows.length} onPageChange={onPageChange} />}>
      <TableHeader headers={["赛日", "马场", "场次", "彩池", "中奖组合", "派彩"]} />
      <tbody>
        {data.rows.map((row) => (
          <tr key={`${row.raceDate}-${row.racecourse}-${row.raceNo}-${row.pool}-${row.winningCombination}-${row.dividend}`} className="border-b border-hairline text-body last:border-0">
            <td className="px-5 py-4 text-ink">{row.raceDate}</td>
            <td className="px-5 py-4">{row.racecourse ?? "-"}</td>
            <td className="px-5 py-4">R{row.raceNo}</td>
            <td className="px-5 py-4"><Badge>{row.pool}</Badge></td>
            <td className="px-5 py-4 text-ink">{row.winningCombination}</td>
            <td className="px-5 py-4">{row.dividend}</td>
          </tr>
        ))}
      </tbody>
    </DataCard>
  );
}

function PredictionTable({ rows, page, onPageChange }: { rows: PredictionRow[]; page: number; onPageChange: (page: number) => void }) {
  const data = paged(rows, page);
  return (
    <DataCard footer={<Pagination page={data.safePage} totalPages={data.totalPages} totalRows={rows.length} onPageChange={onPageChange} />}>
      <TableHeader headers={["赛日", "场次", "马匹", "胜率", "位置率", "公允赔率", "市场概率", "Edge", "信号"]} />
      <tbody>
        {data.rows.map((row) => (
          <tr key={`${row.raceDate}-${row.racecourse}-${row.raceNo}-${row.horseCode}`} className="border-b border-hairline text-body last:border-0">
            <td className="px-5 py-4 text-ink">{row.raceDate}</td>
            <td className="px-5 py-4">{row.racecourse} R{row.raceNo}</td>
            <td className="px-5 py-4 text-ink">{row.horseName} ({row.horseCode})</td>
            <td className="px-5 py-4">{percent(row.winProbability)}</td>
            <td className="px-5 py-4">{percent(row.placeProbability)}</td>
            <td className="px-5 py-4">{number(row.fairWinOdds)}</td>
            <td className="px-5 py-4">{row.marketWinProbability == null ? "-" : percent(row.marketWinProbability)}</td>
            <td className="px-5 py-4 text-ink">{row.edge == null ? "-" : percent(row.edge)}</td>
            <td className="px-5 py-4">{row.isValueBet ? <Badge>Value</Badge> : "-"}</td>
          </tr>
        ))}
      </tbody>
    </DataCard>
  );
}

function DataCompletenessPanel({
  activeCategory,
  horseHistoryCoverage,
  discoveredHorseCount,
  coveredHorseCount,
  activeJobs,
  doneJobs,
  skippedJobs,
  completionRate,
}: {
  activeCategory: DataCategory;
  horseHistoryCoverage: number;
  discoveredHorseCount: number;
  coveredHorseCount: number;
  activeJobs: number;
  doneJobs: number;
  skippedJobs: number;
  completionRate: number;
}) {
  const isHorseHistory = activeCategory === "horseHistory";
  const isOddsDeferred = activeCategory === "sources";
  return (
    <div className="mb-4 grid gap-3 lg:grid-cols-4">
      <StatusPill
        label="马匹历史覆盖"
        value={`${coveredHorseCount} / ${discoveredHorseCount || 0}`}
        tone={isHorseHistory && horseHistoryCoverage < 95 ? "warning" : "default"}
      />
      <StatusPill label="官方回填进度" value={`${completionRate}% (${doneJobs} done)`} tone={activeJobs > 0 ? "warning" : "success"} />
      <StatusPill label="待处理任务" value={activeJobs > 0 ? `${activeJobs} 个` : "已完成"} tone={activeJobs > 0 ? "warning" : "success"} />
      <StatusPill label="非官方赛日" value={`${skippedJobs} skipped`} tone={skippedJobs > 0 ? "warning" : "default"} />
      {isOddsDeferred && <StatusPill label="赔率完整库" value="后置开发" tone="warning" />}
    </div>
  );
}

function ProbabilityPredictionTable({ rows }: { rows: PredictionRow[] }) {
  if (!rows.length) {
    return <div className="px-6 py-5 text-sm text-charcoal">暂无概率预测记录。</div>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <TableHeader headers={["赛事", "马匹", "胜率", "位置概率", "模型版本"]} />
        <tbody>
          {rows.map((row) => (
            <tr key={`probability-${row.raceDate}-${row.racecourse}-${row.raceNo}-${row.horseCode}`} className="border-b border-hairline text-body last:border-0">
              <td className="px-5 py-4">{row.racecourse} R{row.raceNo}</td>
              <td className="px-5 py-4 text-ink">{row.horseNo}. {row.horseName}</td>
              <td className="px-5 py-4 text-ink">{percent(row.winProbability)}</td>
              <td className="px-5 py-4">{percent(row.placeProbability)}</td>
              <td className="px-5 py-4 text-charcoal">{row.modelVersion}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BettingAdviceTable({ rows }: { rows: PredictionRow[] }) {
  if (!rows.length) {
    return <div className="px-6 py-5 text-sm text-charcoal">当前筛选条件下暂无下注候选。</div>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <TableHeader headers={["赛事", "马匹", "市场概率", "公允赔率", "Edge", "候选状态"]} />
        <tbody>
          {rows.map((row) => (
            <tr key={`advice-${row.raceDate}-${row.racecourse}-${row.raceNo}-${row.horseCode}`} className="border-b border-hairline text-body last:border-0">
              <td className="px-5 py-4">{row.racecourse} R{row.raceNo}</td>
              <td className="px-5 py-4 text-ink">{row.horseNo}. {row.horseName}</td>
              <td className="px-5 py-4">{row.marketWinProbability == null ? "-" : percent(row.marketWinProbability)}</td>
              <td className="px-5 py-4">{number(row.fairWinOdds)}</td>
              <td className="px-5 py-4 text-ink">{row.edge == null ? "-" : percent(row.edge)}</td>
              <td className="px-5 py-4"><CandidateBadge prediction={row} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function JobTable({ rows, page, onPageChange }: { rows: ScrapeJob[]; page: number; onPageChange: (page: number) => void }) {
  const data = paged(rows, page);
  return (
    <DataCard footer={<Pagination page={data.safePage} totalPages={data.totalPages} totalRows={rows.length} onPageChange={onPageChange} />}>
      <TableHeader headers={["赛日", "马场", "状态", "次数", "开始", "完成", "错误"]} />
      <tbody>
        {data.rows.map((row) => (
          <tr key={`${row.raceDate}-${row.racecourse}`} className="border-b border-hairline text-body last:border-0">
            <td className="px-5 py-4 text-ink">{row.raceDate}</td>
            <td className="px-5 py-4">{row.racecourse}</td>
            <td className="px-5 py-4"><Badge>{row.status}</Badge></td>
            <td className="px-5 py-4">{row.attempts}</td>
            <td className="px-5 py-4 text-charcoal">{row.startedAt ?? "-"}</td>
            <td className="px-5 py-4 text-charcoal">{row.finishedAt ?? "-"}</td>
            <td className="px-5 py-4 text-charcoal">{row.lastError ?? "-"}</td>
          </tr>
        ))}
      </tbody>
    </DataCard>
  );
}

function CompactRaceList({ rows }: { rows: RaceRow[] }) {
  if (!rows.length) {
    return <p className="text-sm text-charcoal">暂无赛事元数据。</p>;
  }
  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <div key={`${row.raceDate}-${row.racecourse}-${row.raceNo}`} className="flex items-center justify-between border-b border-hairline py-3 last:border-0">
          <div>
            <div className="text-sm text-ink">{row.racecourse} R{row.raceNo} · {row.raceName ?? "-"}</div>
            <div className="mt-1 text-xs text-charcoal">{row.raceClass ?? "-"} · {row.distanceM ?? "-"}m · {row.going ?? "-"}</div>
          </div>
          <Trophy className="size-4 text-accent-yellow" />
        </div>
      ))}
    </div>
  );
}

function FeatureCard({ title, items }: { title: string; items: string[] }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item} className="flex items-center gap-2 text-sm text-body">
              <ListChecks className="size-4 text-accent-green" />
              {item}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function PageShell({ title, eyebrow, children }: { title: string; eyebrow: string; children: ReactNode }) {
  return (
    <div className="min-h-screen px-5 py-5">
      <header className="mb-5 border-b border-hairline pb-5">
        <Badge>{eyebrow}</Badge>
        <h1 className="mt-4 font-display text-5xl leading-none tracking-[-0.96px]">{title}</h1>
      </header>
      {children}
    </div>
  );
}

function DashboardMetric({ icon, title, value, note }: { icon: ReactNode; title: string; value: string; note: string }) {
  return (
    <div className="rounded-lg border border-hairline-strong bg-surface-card p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm text-charcoal">{title}</span>
        <span className="grid size-8 place-items-center rounded-full border border-hairline bg-surface-deep text-accent-green">
          {icon}
        </span>
      </div>
      <div className="mt-5 text-3xl font-medium leading-none text-ink">{value}</div>
      <p className="mt-2 text-sm text-charcoal">{note}</p>
    </div>
  );
}

function StatusPill({ label, value, tone = "default" }: { label: string; value: string; tone?: "default" | "success" | "warning" }) {
  const toneClass =
    tone === "success"
      ? "border-accent-green/40 bg-accent-green/10"
      : tone === "warning"
        ? "border-accent-yellow/40 bg-accent-yellow/10"
        : "border-hairline bg-surface-deep";
  return (
    <div className={`rounded-md border px-3 py-2 ${toneClass}`}>
      <div className="text-xs text-ash">{label}</div>
      <div className="mt-1 text-sm font-medium text-ink">{value}</div>
    </div>
  );
}

function RaceTabs({ raceNos, activeRaceNo, onChange }: { raceNos: number[]; activeRaceNo: number; onChange: (raceNo: number) => void }) {
  if (!raceNos.length) {
    return <div className="border-b border-hairline py-4 text-sm text-charcoal">暂无可切换场次。</div>;
  }

  return (
    <div className="border-b border-hairline py-4">
      <ScrollArea>
        <div className="flex min-w-max gap-2">
          {raceNos.map((raceNo) => (
            <button
              key={raceNo}
              className={[
                "h-10 whitespace-nowrap rounded-full px-4 text-sm transition-colors",
                activeRaceNo === raceNo
                  ? "bg-primary text-primary-on"
                  : "border border-hairline-strong bg-surface-card text-charcoal hover:text-ink",
              ].join(" ")}
              type="button"
              onClick={() => onChange(raceNo)}
            >
              第 {raceNo} 场
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

function StrategyCard({ title, value, note }: { title: string; value: string; note: string }) {
  return (
    <div className="rounded-lg border border-hairline bg-surface-deep p-4">
      <div className="text-sm text-charcoal">{title}</div>
      <div className="mt-3 min-h-8 text-xl font-medium leading-8 text-ink">{value}</div>
      <p className="mt-2 text-sm leading-6 text-ash">{note}</p>
    </div>
  );
}

function RaceRunnerTable({ results, predictions }: { results: ResultRow[]; predictions: PredictionRow[] }) {
  const predictionByHorseCode = new Map(predictions.map((prediction) => [prediction.horseCode, prediction]));
  const predictionByHorseNo = new Map(predictions.map((prediction) => [prediction.horseNo, prediction]));
  const rows = results.length
    ? results
    : predictions.map<ResultRow>((prediction) => ({
        raceDate: prediction.raceDate,
        racecourse: prediction.racecourse,
        raceNo: prediction.raceNo,
        place: "-",
        horseNo: prediction.horseNo,
        horseName: prediction.horseName,
        horseCode: prediction.horseCode,
        jockey: "-",
        trainer: "-",
        draw: "-",
        lbw: "-",
        finishTime: "-",
        winOdds: "-",
      }));

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <TableHeader headers={["马号", "马匹", "骑师", "练马师", "档位", "独赢", "模型胜率", "市场概率", "Edge", "公允赔率", "候选状态"]} />
        <tbody>
          {rows.map((row) => {
            const prediction = (row.horseCode ? predictionByHorseCode.get(row.horseCode) : undefined) ?? predictionByHorseNo.get(row.horseNo);
            return (
              <tr key={`${row.raceDate}-${row.racecourse}-${row.raceNo}-${row.horseNo}`} className="border-b border-hairline text-body last:border-0">
                <td className="px-5 py-4 text-ink">{row.horseNo}</td>
                <td className="px-5 py-4 text-ink">{row.horseName}{row.horseCode ? ` (${row.horseCode})` : ""}</td>
                <td className="px-5 py-4">{row.jockey}</td>
                <td className="px-5 py-4">{row.trainer}</td>
                <td className="px-5 py-4">{row.draw}</td>
                <td className="px-5 py-4">{row.winOdds}</td>
                <td className="px-5 py-4">{prediction ? percent(prediction.winProbability) : "-"}</td>
                <td className="px-5 py-4">{prediction?.marketWinProbability == null ? "-" : percent(prediction.marketWinProbability)}</td>
                <td className="px-5 py-4 text-ink">{prediction?.edge == null ? "-" : percent(prediction.edge)}</td>
                <td className="px-5 py-4">{prediction?.fairWinOdds == null ? "-" : number(prediction.fairWinOdds)}</td>
                <td className="px-5 py-4">{prediction ? <CandidateBadge prediction={prediction} /> : "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function BetCombinationList({
  primaryPick,
  placePicks,
  quinellaPicks,
}: {
  primaryPick?: PredictionRow;
  placePicks: PredictionRow[];
  quinellaPicks: PredictionRow[];
}) {
  const rows = [
    {
      label: "独赢",
      value: primaryPick ? `${primaryPick.horseNo}. ${primaryPick.horseName}` : "暂无",
      note: primaryPick ? `公允赔率 ${number(primaryPick.fairWinOdds)} · 市场概率 ${primaryPick.marketWinProbability == null ? "-" : percent(primaryPick.marketWinProbability)}` : "需要本场预测输出",
    },
    {
      label: "位置",
      value: placePicks.length ? placePicks.map((pick) => `${pick.horseNo}. ${pick.horseName}`).join(" / ") : "暂无",
      note: "取位置概率最高的 3 匹作为候选篮子。",
    },
    {
      label: "连赢 / 位置Q",
      value: quinellaPicks.length >= 2 ? quinellaPicks.map((pick) => `${pick.horseNo}. ${pick.horseName}`).join(" + ") : "暂无",
      note: "取胜率最高的 2 匹作为组合候选。",
    },
  ];

  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div key={row.label} className="rounded-lg border border-hairline bg-surface-deep p-4">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-charcoal">{row.label}</span>
            <SlidersHorizontal className="size-4 text-accent-blue" />
          </div>
          <div className="mt-3 text-sm font-medium leading-6 text-ink">{row.value}</div>
          <p className="mt-2 text-xs leading-5 text-ash">{row.note}</p>
        </div>
      ))}
    </div>
  );
}

function DividendSummary({ rows }: { rows: DividendRow[] }) {
  if (!rows.length) {
    return <p className="text-sm text-charcoal">暂无本场派彩记录。</p>;
  }

  return (
    <div className="space-y-2">
      {rows.slice(0, 6).map((row) => (
        <div key={`${row.pool}-${row.winningCombination}-${row.dividend}`} className="flex items-center justify-between gap-3 border-b border-hairline py-2 text-sm last:border-0">
          <span className="text-charcoal">{row.pool}</span>
          <span className="text-right text-ink">{row.winningCombination} · {row.dividend}</span>
        </div>
      ))}
    </div>
  );
}

function EquityCurve({ points, initialBankroll }: { points: BacktestEquityPoint[]; initialBankroll: number }) {
  if (!points.length) {
    return <p className="text-sm text-charcoal">暂无资金曲线。请先运行回测。</p>;
  }
  const values = [initialBankroll, ...points.map((point) => point.bankroll)];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1, max - min);

  return (
    <div className="space-y-3">
      {points.map((point) => {
        const width = 10 + ((point.bankroll - min) / span) * 90;
        return (
          <div key={point.sequence} className="grid gap-2 sm:grid-cols-[96px_minmax(0,1fr)_96px] sm:items-center">
            <div className="text-sm text-charcoal">#{point.sequence} R{point.race_no}</div>
            <div className="h-3 overflow-hidden rounded-full bg-surface-deep">
              <div className="h-full rounded-full bg-primary" style={{ width: `${width}%` }} />
            </div>
            <div className="text-sm text-ink sm:text-right">{money(point.bankroll)}</div>
          </div>
        );
      })}
    </div>
  );
}

function BacktestBetTable({ rows }: { rows: BacktestBet[] }) {
  if (!rows.length) {
    return <div className="p-6 text-sm text-charcoal">暂无投注明细。</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <TableHeader headers={["序号", "赛日", "场次", "马匹", "类型", "概率", "赔率", "注码", "盈亏", "资金", "结果"]} />
        <tbody>
          {rows.map((row) => (
            <tr key={row.sequence} className="border-b border-hairline text-body last:border-0">
              <td className="px-5 py-4 text-ink">{row.sequence}</td>
              <td className="px-5 py-4">{row.race_date}</td>
              <td className="px-5 py-4">{row.racecourse} R{row.race_no}</td>
              <td className="px-5 py-4 text-ink">{row.horse_no}. {row.horse_name}</td>
              <td className="px-5 py-4"><Badge>{row.bet_type}</Badge></td>
              <td className="px-5 py-4">{percent(row.model_probability)}</td>
              <td className="px-5 py-4">{row.decimal_odds == null ? "-" : number(row.decimal_odds)}</td>
              <td className="px-5 py-4">{money(row.stake)}</td>
              <td className={["px-5 py-4", row.profit_loss >= 0 ? "text-accent-green" : "text-accent-red"].join(" ")}>
                {money(row.profit_loss)}
              </td>
              <td className="px-5 py-4 text-ink">{money(row.bankroll_after)}</td>
              <td className="px-5 py-4">{row.is_hit ? <Badge>命中</Badge> : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OddsChangeTable({
  rows,
  activeValue,
  onSelect,
}: {
  rows: OddsSeries[];
  activeValue: string;
  onSelect: (value: string) => void;
}) {
  if (!rows.length) {
    return <div className="p-6 text-sm text-charcoal">暂无赔率变化数据。</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <TableHeader headers={["对象", "快照", "初始赔率", "最新赔率", "变化", "首末时间"]} />
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.oddsValue}
              className={[
                "cursor-pointer border-b border-hairline text-body transition-colors last:border-0 hover:bg-surface-deep",
                activeValue === row.oddsValue ? "bg-surface-elevated text-ink" : "",
              ].join(" ")}
              onClick={() => onSelect(row.oddsValue)}
            >
              <td className="px-5 py-4 text-ink">{row.oddsValue}</td>
              <td className="px-5 py-4">{row.snapshotCount}</td>
              <td className="px-5 py-4">{number(row.firstOdds)}</td>
              <td className="px-5 py-4">{number(row.lastOdds)}</td>
              <td className={["px-5 py-4", (row.change ?? 0) >= 0 ? "text-accent-green" : "text-accent-red"].join(" ")}>
                {row.change == null ? "-" : number(row.change)}
              </td>
              <td className="px-5 py-4 text-charcoal">
                {row.points[0]?.snapshotAt ?? "-"} → {row.points[row.points.length - 1]?.snapshotAt ?? "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OddsSparkline({ series }: { series?: OddsSeries }) {
  if (!series || series.points.length < 2) {
    return <p className="text-sm text-charcoal">暂无足够快照绘制曲线。</p>;
  }
  const width = 320;
  const height = 140;
  const values = series.points.map((point) => point.odds);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(0.0001, max - min);
  const points = values.map((value, index) => {
    const x = (index / Math.max(1, values.length - 1)) * width;
    const y = height - ((value - min) / span) * (height - 16) - 8;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");

  return (
    <div>
      <svg className="h-40 w-full overflow-visible" preserveAspectRatio="none" viewBox={`0 0 ${width} ${height}`}>
        <polyline fill="none" points={points} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" className="text-accent-blue" />
      </svg>
      <div className="mt-4 grid grid-cols-3 gap-3">
        <StatusPill label="最低" value={number(min)} />
        <StatusPill label="最高" value={number(max)} />
        <StatusPill label="变化" value={series.change == null ? "-" : number(series.change)} />
      </div>
    </div>
  );
}

function OddsSnapshotList({ points }: { points: OddsPoint[] }) {
  if (!points.length) {
    return <p className="text-sm text-charcoal">暂无快照。</p>;
  }
  return (
    <div className="max-h-[360px] space-y-2 overflow-y-auto pr-1">
      {points.slice(-20).map((point) => (
        <div key={point.legacyId} className="flex items-center justify-between gap-3 border-b border-hairline py-2 text-sm last:border-0">
          <span className="text-charcoal">{point.snapshotAt}</span>
          <span className="text-ink">{number(point.odds)}</span>
        </div>
      ))}
    </div>
  );
}

function ProgressTrack({ value }: { value: number }) {
  const safeValue = Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-charcoal">历史赛日采集完成度</span>
        <span className="text-ink">{safeValue}%</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-deep">
        <div className="h-full rounded-full bg-primary" style={{ width: `${safeValue}%` }} />
      </div>
    </div>
  );
}

function MetricCard({ title, value, note }: { title: string; value: string; note: string }) {
  return (
    <Card>
      <CardHeader className="p-5 pb-2"><CardTitle className="text-base leading-6">{title}</CardTitle></CardHeader>
      <CardContent className="p-5 pt-2">
        <div className="text-3xl font-medium">{value}</div>
        <p className="mt-2 text-sm text-charcoal">{note}</p>
      </CardContent>
    </Card>
  );
}

function StatusLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-hairline py-2 last:border-0">
      <span className="text-charcoal">{label}</span>
      <span className="text-ink">{value}</span>
    </div>
  );
}

function CandidateBadge({ prediction }: { prediction: PredictionRow }) {
  if (prediction.isValueBet) {
    return <Badge>下注候选</Badge>;
  }
  if ((prediction.edge ?? 0) > 0) {
    return <span className="text-accent-blue">观察</span>;
  }
  return <span className="text-charcoal">过滤</span>;
}

function BacktestParameterPanel({
  config,
  onChange,
}: {
  config: BacktestFormState;
  onChange: (field: keyof BacktestFormState, value: string) => void;
}) {
  return (
    <Card>
      <CardHeader className="p-6 pb-2">
        <CardTitle>回测参数</CardTitle>
        <p className="mt-1 text-sm text-charcoal">配置投注类型、下注策略、边际阈值、概率阈值、候选数和日期范围。</p>
      </CardHeader>
      <CardContent className="grid gap-4 p-6 pt-3 md:grid-cols-2 xl:grid-cols-3">
        <FormSelect label="投注类型" value={config.betType} options={["win", "place"]} onChange={(value) => onChange("betType", value)} />
        <FormSelect label="下注策略" value={config.stakeStrategy} options={["flat", "kelly_fraction", "proportional"]} onChange={(value) => onChange("stakeStrategy", value)} />
        <FormInput label="单注金额" type="number" value={config.flatStake} onChange={(value) => onChange("flatStake", value)} />
        <FormInput label="Min edge" type="number" value={config.minEdge} onChange={(value) => onChange("minEdge", value)} />
        <FormInput label="Min probability" type="number" value={config.minProbability} onChange={(value) => onChange("minProbability", value)} />
        <FormInput label="Top N" type="number" value={config.topN} onChange={(value) => onChange("topN", value)} />
        <FormInput label="开始日期" type="date" value={config.startDate} onChange={(value) => onChange("startDate", value)} />
        <FormInput label="结束日期" type="date" value={config.endDate} onChange={(value) => onChange("endDate", value)} />
        <div className="rounded-md border border-hairline bg-surface-deep p-3 text-sm leading-6 text-charcoal">
          当前面板用于固化策略输入；重新运行回测时应把这些参数传给后端回测任务。
        </div>
      </CardContent>
    </Card>
  );
}

function FormInput({
  label,
  value,
  type,
  onChange,
}: {
  label: string;
  value: string;
  type: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-2 block text-charcoal">{label}</span>
      <input
        className="h-10 w-full rounded-md border border-hairline-strong bg-surface-deep px-3 text-ink outline-none focus:border-ink"
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function FormSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-2 block text-charcoal">{label}</span>
      <select
        className="h-10 w-full rounded-md border border-hairline-strong bg-surface-deep px-3 text-ink outline-none focus:border-ink"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}

function ModelVersionMenu({
  options,
  selectedKey,
  onSelect,
}: {
  options: Array<{ key: string; label: string }>;
  selectedKey: string;
  onSelect: (key: string) => void;
}) {
  const active = options.find((option) => option.key === selectedKey) ?? options[0];
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost">
          <SlidersHorizontal className="mr-2 size-4" />
          {active?.label ?? "全部模型"}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {options.map((option) => (
          <DropdownMenuItem key={option.key} onClick={() => onSelect(option.key)}>
            {option.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function RiskNotice() {
  return (
    <div className="mt-4 rounded-md border border-accent-red/40 bg-accent-red/10 px-3 py-2 text-sm leading-6 text-accent-red">
      result_final 使用赛后最终赔率，仅用于对照实验，不能作为实盘赛前信号。
    </div>
  );
}

function DataCard({ children, footer }: { children: ReactNode; footer?: ReactNode }) {
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">{children}</table>
      </div>
      {footer}
    </Card>
  );
}

function TableHeader({ headers }: { headers: string[] }) {
  return (
    <thead className="bg-surface-deep text-left text-xs uppercase tracking-[0.35px] text-ash">
      <tr>
        {headers.map((header) => (
          <th key={header} className="whitespace-nowrap border-b border-hairline px-5 py-4 font-medium">
            {header}
          </th>
        ))}
      </tr>
    </thead>
  );
}

function Pagination({
  page,
  totalPages,
  totalRows,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  totalRows: number;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="flex items-center justify-between border-t border-hairline bg-surface-deep px-5 py-4">
      <div className="text-sm text-charcoal">第 {page} / {totalPages} 页，共 {totalRows} 条</div>
      <div className="flex gap-2">
        <Button disabled={page === 1} variant="ghost" onClick={() => onPageChange(Math.max(1, page - 1))}>
          <ChevronLeft className="mr-1 size-4" />
          上一页
        </Button>
        <Button disabled={page === totalPages} variant="ghost" onClick={() => onPageChange(Math.min(totalPages, page + 1))}>
          下一页
          <ChevronRight className="ml-1 size-4" />
        </Button>
      </div>
    </div>
  );
}

function RaceQuantLogo() {
  return (
    <div className="grid size-9 place-items-center rounded-lg border border-hairline-strong bg-surface-elevated">
      <svg aria-hidden="true" className="size-6" fill="none" viewBox="0 0 28 28">
        <path className="text-ink" d="M14 3.5c6.2 0 10 3.1 10 7.2 0 5.9-5.8 13.8-10 13.8S4 16.6 4 10.7c0-4.1 3.8-7.2 10-7.2Z" stroke="currentColor" strokeWidth="1.5" />
        <path className="text-accent-green" d="M8.2 17.4 11.4 14l3 2.3 5.4-7" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
        <path className="text-charcoal" d="M8.8 10.5c1.1-1.4 2.8-2.2 5.2-2.2 2.5 0 4.3.8 5.3 2.3" stroke="currentColor" strokeLinecap="round" strokeWidth="1.2" />
        <circle className="fill-accent-blue" cx="19.8" cy="9.3" r="1.4" />
      </svg>
    </div>
  );
}

function pageFromPath(pathname: string): Page {
  if (pathname.startsWith("/data")) return "data";
  if (pathname.startsWith("/odds")) return "odds";
  if (pathname.startsWith("/model")) return "model";
  if (pathname.startsWith("/features")) return "features";
  if (pathname.startsWith("/backtests")) return "backtests";
  if (pathname.startsWith("/settings")) return "settings";
  return "dashboard";
}

function isDataCategory(value: string | undefined): value is DataCategory {
  return (
    value === "sources" ||
    value === "races" ||
    value === "entries" ||
    value === "horseHistory" ||
    value === "changeEvents" ||
    value === "results" ||
    value === "dividends" ||
    value === "jobs"
  );
}

function changeEventLabel(value: string) {
  const labels: Record<string, string> = {
    scratched: "退赛",
    standby_promoted: "候补补上",
    jockey_change: "换骑师",
    weight_change: "负磅",
  };
  return labels[value] ?? value;
}

function paged<T>(rows: T[], page: number) {
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(page, totalPages);
  return {
    rows: rows.slice((safePage - 1) * pageSize, safePage * pageSize),
    safePage,
    totalPages,
  };
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("zh-Hans-CN").format(value);
}

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function number(value: number | null) {
  return value == null ? "-" : value.toFixed(2);
}

function money(value: number | null) {
  if (value == null || Number.isNaN(value)) return "-";
  return new Intl.NumberFormat("zh-Hans-CN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(value);
}

function groupCount(values: string[]) {
  return values.reduce<Record<string, number>>((acc, value) => {
    acc[value] = (acc[value] ?? 0) + 1;
    return acc;
  }, {});
}

function stringConfig(config: Record<string, unknown>, key: string) {
  const value = config[key];
  return typeof value === "string" && value ? value : "";
}

function optionalStringConfig(config: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const value = config[key];
    if (typeof value === "string" && value) return value;
    if (typeof value === "number" && Number.isFinite(value)) return String(value);
  }
  return "";
}

function backtestFormFromConfig(config: Record<string, unknown>): BacktestFormState {
  return {
    betType: optionalStringConfig(config, "bet_type", "betType") || "win",
    stakeStrategy: optionalStringConfig(config, "stake_strategy", "stakeStrategy") || "flat",
    flatStake: optionalStringConfig(config, "flat_stake", "flatStake") || "10",
    minEdge: optionalStringConfig(config, "min_edge", "minEdge") || "0.03",
    minProbability: optionalStringConfig(config, "min_probability", "minProbability") || "0",
    topN: optionalStringConfig(config, "top_n_per_race", "topNPerRace") || "1",
    startDate: optionalStringConfig(config, "start_date", "startDate"),
    endDate: optionalStringConfig(config, "end_date", "endDate"),
  };
}

function modelMetadata(predictions: PredictionRow[]) {
  const row = predictions[0];
  const oddsMode = row?.oddsMode ?? "-";
  return {
    oddsMode,
    trainingDatasetVersion: row?.trainingDatasetVersion ?? "-",
    featureVersion: row?.featureVersion ?? "-",
    dataBuildId: row?.dataBuildId ?? "-",
    isLeakageRisk: oddsMode === "result_final",
  };
}

function modelKey(row: PredictionRow) {
  return [row.modelName, row.modelVersion, row.oddsMode ?? "none"].join("::");
}

function jobStatusCounts(jobs: ScrapeJob[]) {
  return jobs.reduce(
    (counts, job) => {
      if (job.status === "done") counts.done += 1;
      else if (job.status === "running") counts.running += 1;
      else if (job.status === "failed") counts.failed += 1;
      else if (job.status === "skipped_no_official_result") counts.skipped += 1;
      else counts.pending += 1;
      return counts;
    },
    { done: 0, pending: 0, running: 0, failed: 0, skipped: 0 },
  );
}

function modelVersionOptions(predictions: PredictionRow[]) {
  const options = new Map<string, string>();
  for (const row of predictions) {
    options.set(modelKey(row), `${row.modelName} / ${row.modelVersion} / ${row.oddsMode ?? "none"}`);
  }
  return [{ key: "all", label: "全部模型" }, ...Array.from(options, ([key, label]) => ({ key, label }))];
}

async function loadJson<T>(url: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}
