import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BadgeCheck,
  Bot,
  BrainCircuit,
  CheckCircle2,
  Copy,
  FileSearch,
  Gauge,
  HelpCircle,
  MapPin,
  MessageSquareText,
  Radar,
  ScanText,
  Send,
  Sparkles,
  TimerReset
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { askReportQuestion } from "../services/api";
import { AnalysisResponse, RiskFactor, RiskLevel } from "../types/analysis";
import { BreakdownGrid } from "./BreakdownGrid";
import { RiskGauge } from "./RiskGauge";

type ReportTab = "overview" | "claims" | "signals" | "operations" | "assistant";

const tabs: Array<{ id: ReportTab; label: string; icon: LucideIcon }> = [
  { id: "overview", label: "Overview", icon: Gauge },
  { id: "claims", label: "Claims", icon: FileSearch },
  { id: "signals", label: "Signals", icon: Radar },
  { id: "operations", label: "Operations", icon: BrainCircuit },
  { id: "assistant", label: "Assistant", icon: MessageSquareText }
];

function riskTone(risk: RiskLevel) {
  if (risk === "low") return "border-moss/30 bg-moss/10 text-moss";
  if (risk === "medium") return "border-saffron/30 bg-saffron/10 text-saffron";
  return "border-coral/30 bg-coral/10 text-coral";
}

function riskDot(risk: RiskLevel) {
  if (risk === "low") return "bg-moss";
  if (risk === "medium") return "bg-saffron";
  return "bg-coral";
}

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

function metricTone(value: number, inverse = false) {
  const score = inverse ? 100 - value : value;
  if (score >= 75) return "text-moss";
  if (score >= 50) return "text-saffron";
  return "text-coral";
}

export function ResultPanel({ result }: { result: AnalysisResponse | null }) {
  const [activeTab, setActiveTab] = useState<ReportTab>("overview");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);

  useEffect(() => {
    setActiveTab("overview");
    setQuestion("");
    setAnswer(null);
    setAskError(null);
  }, [result?.analysis_id]);

  const topRisks = useMemo(() => {
    if (!result) return [];
    return [...result.risk_factors]
      .sort((a, b) => riskSeverity(b) - riskSeverity(a) || b.score - a.score)
      .slice(0, 3);
  }, [result]);

  async function handleAsk() {
    if (!result || question.trim().length < 2) return;

    setAsking(true);
    setAskError(null);
    try {
      const response = await askReportQuestion(result.analysis_id, question.trim());
      setAnswer(response.answer);
    } catch (error) {
      setAskError(error instanceof Error ? error.message : "Question failed.");
    } finally {
      setAsking(false);
    }
  }

  if (!result) {
    return (
      <section className="grid min-h-[620px] place-items-center rounded-lg border border-line bg-white shadow-panel">
        <div className="mx-auto max-w-sm text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-lg border border-line bg-paper">
            <Gauge className="h-7 w-7 text-graphite" aria-hidden="true" />
          </div>
          <h2 className="mt-5 text-xl font-bold text-ink">No active report</h2>
          <p className="mt-2 text-sm leading-6 text-graphite">Verification output will appear in this workspace.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-lg border border-line bg-white shadow-panel">
      <ReportHeader result={result} />

      <div className="border-b border-line bg-paper/70 px-4 py-3">
        <div className="flex gap-2 overflow-x-auto scrollbar-clean">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`inline-flex h-10 shrink-0 items-center gap-2 rounded-md border px-3 text-sm font-bold transition ${
                  active
                    ? "border-ink bg-ink text-white"
                    : "border-line bg-white text-graphite hover:border-ink/40 hover:text-ink"
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-5 p-5">
        {activeTab === "overview" ? <OverviewTab result={result} topRisks={topRisks} /> : null}
        {activeTab === "claims" ? <ClaimsTab result={result} /> : null}
        {activeTab === "signals" ? <SignalsTab result={result} /> : null}
        {activeTab === "operations" ? <OperationsTab result={result} /> : null}
        {activeTab === "assistant" ? (
          <AssistantTab
            question={question}
            answer={answer}
            asking={asking}
            askError={askError}
            setQuestion={setQuestion}
            handleAsk={handleAsk}
          />
        ) : null}
      </div>
    </section>
  );
}

function ReportHeader({ result }: { result: AnalysisResponse }) {
  return (
    <div className="border-b border-line bg-white px-5 py-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-2 rounded-md border px-2.5 py-1 text-xs font-bold uppercase ${riskTone(result.risk_level)}`}>
              <span className={`h-2 w-2 rounded-full ${riskDot(result.risk_level)}`} />
              {result.risk_level} risk
            </span>
            <span className="rounded-md border border-line bg-paper px-2.5 py-1 text-xs font-bold uppercase text-graphite">
              {formatLabel(result.topic)}
            </span>
            <span className="rounded-md border border-line bg-paper px-2.5 py-1 text-xs font-bold uppercase text-graphite">
              {result.language}
            </span>
          </div>
          <h2 className="mt-3 text-2xl font-bold text-ink">Trust Intelligence Report</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-graphite">{result.summary}</p>
        </div>

        <button
          type="button"
          className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-bold text-graphite transition hover:border-ink/40 hover:text-ink"
          onClick={() => navigator.clipboard?.writeText(JSON.stringify(result, null, 2))}
          title="Copy report JSON"
        >
          <Copy className="h-4 w-4" aria-hidden="true" />
          Copy
        </button>
      </div>
    </div>
  );
}

function OverviewTab({ result, topRisks }: { result: AnalysisResponse; topRisks: RiskFactor[] }) {
  return (
    <>
      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <RiskGauge score={result.trust_score} risk={result.risk_level} />
        <section className="rounded-lg border border-line bg-white p-5">
          <h3 className="text-lg font-bold text-ink">Executive Summary</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <MetricTile icon={BadgeCheck} label="Source" value={result.source_score} />
            <MetricTile icon={FileSearch} label="Evidence" value={result.evidence_quality} />
            <MetricTile icon={AlertTriangle} label="Manipulation" value={result.manipulation_score} inverse />
          </div>
          <div className="mt-4 rounded-md border border-line bg-paper/70 p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-graphite">Recommended action</p>
            <p className="mt-1 text-base font-bold capitalize text-ink">{formatLabel(result.recommended_action)}</p>
          </div>
        </section>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <MetricCard icon={Sparkles} label="AI likelihood" value={result.ai_generated_likelihood} note="Writing-pattern signal" />
        <MetricCard icon={TimerReset} label="Viral risk" value={result.viral_risk} note="Distribution pressure" inverse />
        <MetricCard icon={MapPin} label="Regional sensitivity" value={result.regional_context.sensitivity} note={result.regional_context.region} inverse />
      </section>

      <section className="rounded-lg border border-line bg-white p-5">
        <h3 className="text-lg font-bold text-ink">Priority Risks</h3>
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          {topRisks.map((risk) => (
            <div key={risk.label} className="rounded-md border border-line bg-paper/60 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-bold capitalize text-ink">{formatLabel(risk.label)}</p>
                <span className={`text-sm font-bold risk-${risk.impact}`}>{risk.score}</span>
              </div>
              <p className="mt-2 text-sm leading-6 text-graphite">{risk.explanation}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function ClaimsTab({ result }: { result: AnalysisResponse }) {
  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-line bg-white p-5">
        <h3 className="text-lg font-bold text-ink">Claim Checks</h3>
        <div className="mt-4 divide-y divide-line rounded-md border border-line">
          {result.claim_checks.map((claim) => (
            <div key={`${claim.claim}-${claim.verdict}`} className="p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="max-w-2xl text-sm font-bold leading-6 text-ink">{claim.claim}</p>
                <span className="rounded-md bg-paper px-2.5 py-1 text-xs font-bold uppercase text-graphite">
                  {formatLabel(claim.verdict)}
                </span>
              </div>
              <p className="mt-2 text-sm leading-6 text-graphite">{claim.evidence}</p>
              <p className="mt-1 text-sm leading-6 text-slate-500">{claim.missing_evidence}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-line bg-white p-5">
        <h3 className="text-lg font-bold text-ink">Evidence Notes</h3>
        <div className="mt-4 divide-y divide-line rounded-md border border-line">
          {result.reasoning.map((item) => (
            <div key={`${item.label}-${item.evidence}`} className="p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-bold capitalize text-ink">{formatLabel(item.label)}</p>
                <p className="text-xs font-bold uppercase text-graphite">{item.signal_type}</p>
              </div>
              <p className="mt-2 text-sm leading-6 text-graphite">{item.evidence}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function SignalsTab({ result }: { result: AnalysisResponse }) {
  return (
    <div className="space-y-5">
      <BreakdownGrid breakdown={result.score_breakdown} />

      <section className="rounded-lg border border-line bg-white p-5">
        <h3 className="text-lg font-bold text-ink">Signal Register</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {result.risk_factors.map((factor) => (
            <div key={factor.label} className="rounded-md border border-line bg-paper/60 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-bold capitalize text-ink">{formatLabel(factor.label)}</p>
                <span className={`text-sm font-bold risk-${factor.impact}`}>{factor.score}</span>
              </div>
              <p className="mt-2 text-sm leading-6 text-graphite">{factor.explanation}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-line bg-white p-5">
        <h3 className="text-lg font-bold text-ink">Language And Manipulation</h3>
        <div className="mt-4 flex flex-wrap gap-2">
          {result.manipulation_patterns.length === 0 ? (
            <span className="rounded-md border border-line bg-paper px-3 py-1.5 text-sm font-bold text-graphite">
              No strong pattern detected
            </span>
          ) : (
            result.manipulation_patterns.map((pattern) => (
              <span key={pattern} className="rounded-md border border-coral/20 bg-coral/10 px-3 py-1.5 text-sm font-bold text-coral">
                {formatLabel(pattern)}
              </span>
            ))
          )}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {result.highlight_spans.map((span) => (
            <span key={`${span.text}-${span.type}`} className={`rounded-md border px-3 py-1.5 text-sm font-bold ${riskTone(span.severity)}`}>
              {span.text}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}

function OperationsTab({ result }: { result: AnalysisResponse }) {
  return (
    <div className="space-y-5">
      <section className="grid gap-4 md:grid-cols-3">
        <ContextBlock title="Regional context" body={result.regional_context.note} />
        <ContextBlock title="Community signal" body={result.community_signal.note} />
        <ContextBlock title="Visual authenticity" body={result.visual_authenticity.notes} />
      </section>

      <section className="rounded-lg border border-line bg-white p-5">
        <h3 className="text-lg font-bold text-ink">Trust Timeline</h3>
        <div className="mt-4 divide-y divide-line rounded-md border border-line">
          {result.trust_timeline.map((event) => (
            <div key={`${event.stage}-${event.status}`} className="grid gap-1 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-bold capitalize text-ink">{formatLabel(event.stage)}</p>
                <span className="text-xs font-bold uppercase text-graphite">{event.status}</span>
              </div>
              <p className="text-sm leading-6 text-graphite">{event.note}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-line bg-white p-5">
        <h3 className="text-lg font-bold text-ink">Agent Findings</h3>
        <div className="mt-4 divide-y divide-line rounded-md border border-line">
          {result.agent_findings.map((finding) => (
            <div key={finding.agent} className="p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-bold text-ink">{finding.agent}</p>
                <p className="text-sm font-bold text-graphite">{finding.score}</p>
              </div>
              <p className="mt-2 text-sm leading-6 text-graphite">{finding.summary}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-line bg-white p-5">
        <h3 className="text-lg font-bold text-ink">Runtime</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <MetricTile icon={Bot} label="Model" value={result.cost.model_used} text />
          <MetricTile icon={CheckCircle2} label="OpenAI" value={result.cost.openai_used ? "Used" : "Fallback"} text />
          <MetricTile icon={ScanText} label="Cache" value={result.cost.cache_hit ? "Hit" : "Miss"} text />
        </div>
      </section>
    </div>
  );
}

function AssistantTab(props: {
  question: string;
  answer: string | null;
  asking: boolean;
  askError: string | null;
  setQuestion: (value: string) => void;
  handleAsk: () => void;
}) {
  return (
    <section className="rounded-lg border border-line bg-white p-5">
      <div className="flex items-center gap-2">
        <HelpCircle className="h-5 w-5 text-sky" aria-hidden="true" />
        <h3 className="text-lg font-bold text-ink">Report Assistant</h3>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
        <input
          value={props.question}
          onChange={(event) => props.setQuestion(event.target.value)}
          className="h-12 rounded-md border border-line bg-paper/70 px-3 text-sm outline-none transition focus:border-sky focus:shadow-focus"
          placeholder="Ask about this report"
        />
        <button
          type="button"
          onClick={props.handleAsk}
          disabled={props.asking || props.question.trim().length < 2}
          className="inline-flex h-12 items-center justify-center gap-2 rounded-md bg-ink px-5 text-sm font-bold text-white transition hover:bg-ink/90 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          <Send className="h-4 w-4" aria-hidden="true" />
          {props.asking ? "Thinking" : "Ask"}
        </button>
      </div>
      {props.askError ? <p className="mt-3 text-sm font-bold text-coral">{props.askError}</p> : null}
      {props.answer ? <p className="mt-4 rounded-md border border-line bg-paper/70 p-4 text-sm leading-6 text-graphite">{props.answer}</p> : null}
    </section>
  );
}

function MetricTile(props: { icon: LucideIcon; label: string; value: number | string; inverse?: boolean; text?: boolean }) {
  const Icon = props.icon;
  return (
    <div className="rounded-md border border-line bg-paper/60 p-4">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-graphite" aria-hidden="true" />
        <p className="text-xs font-bold uppercase tracking-wide text-graphite">{props.label}</p>
      </div>
      <p className={`mt-2 text-2xl font-bold ${props.text ? "text-ink" : metricTone(Number(props.value), props.inverse)}`}>
        {props.value}
      </p>
    </div>
  );
}

function MetricCard(props: { icon: LucideIcon; label: string; value: number; note: string; inverse?: boolean }) {
  const Icon = props.icon;
  return (
    <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5 text-graphite" aria-hidden="true" />
        <h3 className="text-sm font-bold uppercase tracking-wide text-graphite">{props.label}</h3>
      </div>
      <p className={`mt-3 text-3xl font-bold ${metricTone(props.value, props.inverse)}`}>{props.value}</p>
      <p className="mt-1 text-sm text-graphite">{props.note}</p>
    </div>
  );
}

function ContextBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
      <p className="font-bold text-ink">{title}</p>
      <p className="mt-2 text-sm leading-6 text-graphite">{body}</p>
    </div>
  );
}

function riskSeverity(factor: RiskFactor) {
  if (factor.impact === "critical") return 4;
  if (factor.impact === "high") return 3;
  if (factor.impact === "medium") return 2;
  return 1;
}
