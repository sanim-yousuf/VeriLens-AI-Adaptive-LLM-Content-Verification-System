import { ShieldCheck, ShieldAlert } from "lucide-react";
import { RiskLevel } from "../types/analysis";

const riskCopy: Record<RiskLevel, string> = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
  critical: "Critical risk"
};

function colorFor(score: number) {
  if (score >= 80) return "#427A5B";
  if (score >= 60) return "#D97706";
  return "#C2413A";
}

export function RiskGauge({ score, risk }: { score: number; risk: RiskLevel }) {
  const color = colorFor(score);
  const degrees = Math.max(0, Math.min(100, score)) * 3.6;
  const Icon = score >= 70 ? ShieldCheck : ShieldAlert;

  return (
    <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-graphite">Trust score</p>
          <h2 className="mt-1 text-4xl font-bold text-ink">{score}</h2>
          <p className={`mt-1 text-sm font-semibold risk-${risk}`}>{riskCopy[risk]}</p>
        </div>
        <div
          className="grid h-32 w-32 place-items-center rounded-full"
          style={{
            background: `conic-gradient(${color} ${degrees}deg, #E6E1D5 ${degrees}deg 360deg)`
          }}
          aria-label={`Trust score ${score}`}
        >
          <div className="grid h-24 w-24 place-items-center rounded-full bg-white">
            <Icon className="h-10 w-10" style={{ color }} aria-hidden="true" />
          </div>
        </div>
      </div>
    </section>
  );
}
