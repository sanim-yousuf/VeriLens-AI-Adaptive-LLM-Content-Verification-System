import { ScoreBreakdown } from "../types/analysis";

const labels: Array<[keyof ScoreBreakdown, string, boolean]> = [
  ["source_credibility", "Source", false],
  ["evidence_consistency", "Evidence", false],
  ["manipulation_intensity", "Manipulation", true],
  ["language_patterns", "Language", false],
  ["context_risk", "Context", true],
  ["visual_authenticity", "Visual", false],
  ["viral_risk", "Viral", true]
];

function barColor(value: number, inverse: boolean) {
  const score = inverse ? 100 - value : value;
  if (score >= 75) return "bg-moss";
  if (score >= 50) return "bg-saffron";
  return "bg-coral";
}

export function BreakdownGrid({ breakdown }: { breakdown: ScoreBreakdown }) {
  return (
    <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
      <h2 className="text-lg font-bold text-ink">Signal Breakdown</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {labels.map(([key, label, inverse]) => {
          const value = breakdown[key];
          return (
            <div key={key}>
              <div className="mb-1 flex items-center justify-between gap-2 text-sm">
                <span className="font-semibold text-slate-700">{label}</span>
                <span className="font-bold text-ink">{value}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div className={`h-full ${barColor(value, inverse)}`} style={{ width: `${value}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
