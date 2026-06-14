import { useState } from "react";
import {
  Activity,
  BarChart3,
  Bell,
  CircleDollarSign,
  DatabaseZap,
  FileSearch,
  Globe2,
  LayoutDashboard,
  LockKeyhole,
  Shield,
  Sparkles
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { InputPanel } from "./components/InputPanel";
import { ResultPanel } from "./components/ResultPanel";
import { createAnalysis } from "./services/api";
import { AnalysisMode, AnalysisResponse, InputType } from "./types/analysis";

export default function App() {
  const [type, setType] = useState<InputType>("text");
  const [mode, setMode] = useState<AnalysisMode>("standard");
  const [content, setContent] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [region, setRegion] = useState("BD");
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);

    try {
      const data = await createAnalysis({
        type,
        content,
        analysis_mode: mode,
        source_url: sourceUrl,
        region
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-surface min-h-screen bg-paper text-ink">
      <div className="grid min-h-screen lg:grid-cols-[248px_1fr]">
        <aside className="hidden border-r border-line bg-white/95 lg:block">
          <div className="flex h-full flex-col">
            <div className="border-b border-line p-5">
              <div className="flex items-center gap-3">
                <div className="grid h-11 w-11 place-items-center rounded-lg bg-ink text-white">
                  <Shield className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-ink">VeriLens AI</h1>
                  <p className="text-xs font-semibold uppercase tracking-wide text-graphite">Trust console</p>
                </div>
              </div>
            </div>

            <nav className="space-y-1 p-3">
              <NavItem icon={LayoutDashboard} label="Workspace" active />
              <NavItem icon={FileSearch} label="Reports" />
              <NavItem icon={BarChart3} label="Signals" />
              <NavItem icon={DatabaseZap} label="Sources" />
              <NavItem icon={CircleDollarSign} label="Runtime cost" />
            </nav>

            <div className="mt-auto border-t border-line p-4">
              <div className="rounded-lg border border-line bg-paper p-4">
                <div className="flex items-center gap-2">
                  <LockKeyhole className="h-4 w-4 text-moss" aria-hidden="true" />
                  <p className="text-sm font-bold text-ink">Private runtime</p>
                </div>
                <p className="mt-2 text-xs leading-5 text-graphite">OpenAI calls stay on the FastAPI server.</p>
              </div>
            </div>
          </div>
        </aside>

        <section className="min-w-0">
          <header className="sticky top-0 z-20 border-b border-line bg-white/95 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 xl:px-8">
              <div>
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-graphite">
                  <Globe2 className="h-4 w-4" aria-hidden="true" />
                  Multilingual verification
                </div>
                <h2 className="mt-1 text-2xl font-bold text-ink">Intelligence Workspace</h2>
              </div>

              <div className="flex items-center gap-2">
                <StatusPill icon={Activity} label={loading ? "Analyzing" : "Ready"} active={loading} />
                <StatusPill icon={Sparkles} label={result ? "Report live" : "No report"} />
                <button
                  type="button"
                  className="grid h-10 w-10 place-items-center rounded-md border border-line bg-white text-graphite transition hover:border-ink/40 hover:text-ink"
                  title="Notifications"
                >
                  <Bell className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            </div>
          </header>

          <div className="px-4 py-6 sm:px-6 xl:px-8">
            <section className="mb-5 grid gap-4 xl:grid-cols-4">
              <CommandMetric label="Mode" value={mode} />
              <CommandMetric label="Input" value={type} />
              <CommandMetric label="Region" value={region} />
              <CommandMetric label="OpenAI" value={result?.cost.openai_used ? "used" : "ready"} />
            </section>

            <div className="grid gap-5 2xl:grid-cols-[minmax(420px,0.82fr)_minmax(680px,1.18fr)]">
              <div className="space-y-4">
                <InputPanel
                  type={type}
                  setType={setType}
                  mode={mode}
                  setMode={setMode}
                  content={content}
                  setContent={setContent}
                  sourceUrl={sourceUrl}
                  setSourceUrl={setSourceUrl}
                  region={region}
                  setRegion={setRegion}
                  loading={loading}
                  onSubmit={handleSubmit}
                />
                {error ? (
                  <div className="rounded-lg border border-coral/30 bg-coral/10 p-4 text-sm font-bold text-coral">
                    {error}
                  </div>
                ) : null}
              </div>

              <ResultPanel result={result} />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function NavItem(props: { icon: LucideIcon; label: string; active?: boolean }) {
  const Icon = props.icon;
  return (
    <button
      type="button"
      className={`flex h-10 w-full items-center gap-3 rounded-md px-3 text-sm font-bold transition ${
        props.active ? "bg-ink text-white" : "text-graphite hover:bg-paper hover:text-ink"
      }`}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      {props.label}
    </button>
  );
}

function StatusPill(props: { icon: LucideIcon; label: string; active?: boolean }) {
  const Icon = props.icon;
  return (
    <div className="hidden h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-bold text-graphite sm:inline-flex">
      <Icon className={`h-4 w-4 ${props.active ? "animate-pulse text-saffron" : "text-moss"}`} aria-hidden="true" />
      {props.label}
    </div>
  );
}

function CommandMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-white px-4 py-3 shadow-panel">
      <p className="text-xs font-bold uppercase tracking-wide text-graphite">{label}</p>
      <p className="mt-1 truncate text-base font-bold capitalize text-ink">{value}</p>
    </div>
  );
}
