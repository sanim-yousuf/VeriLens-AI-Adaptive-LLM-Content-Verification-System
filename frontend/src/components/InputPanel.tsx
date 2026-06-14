import {
  ClipboardCheck,
  FileImage,
  Gauge,
  Globe2,
  Loader2,
  LockKeyhole,
  Radar,
  ShieldCheck,
  WifiOff
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { AnalysisMode, InputType } from "../types/analysis";

const typeOptions: Array<{ value: InputType; label: string; icon: LucideIcon }> = [
  { value: "text", label: "Text", icon: ClipboardCheck },
  { value: "url", label: "URL", icon: Globe2 },
  { value: "screenshot", label: "Screenshot", icon: FileImage }
];

const modes: Array<{ value: AnalysisMode; label: string; icon: LucideIcon }> = [
  { value: "quick", label: "Quick", icon: Gauge },
  { value: "standard", label: "Standard", icon: ShieldCheck },
  { value: "deep", label: "Deep", icon: Radar },
  { value: "offline", label: "Offline", icon: WifiOff }
];

interface InputPanelProps {
  type: InputType;
  setType: (type: InputType) => void;
  mode: AnalysisMode;
  setMode: (mode: AnalysisMode) => void;
  content: string;
  setContent: (content: string) => void;
  sourceUrl: string;
  setSourceUrl: (url: string) => void;
  region: string;
  setRegion: (region: string) => void;
  loading: boolean;
  onSubmit: () => void;
}

export function InputPanel(props: InputPanelProps) {
  const canSubmit = props.content.trim().length > 0 && !props.loading;
  const charCount = props.content.trim().length;

  return (
    <section className="overflow-hidden rounded-lg border border-line bg-white shadow-panel">
      <div className="border-b border-line px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-ink">Intake</h2>
            <p className="mt-1 text-sm text-graphite">Case workspace</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-md border border-line bg-paper px-3 py-2 text-xs font-bold uppercase text-graphite">
            <LockKeyhole className="h-4 w-4 text-moss" aria-hidden="true" />
            Server side API
          </div>
        </div>
      </div>

      <div className="space-y-5 p-5">
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-graphite">Input type</p>
          <div className="grid grid-cols-3 gap-2">
            {typeOptions.map((option) => {
              const Icon = option.icon;
              const active = props.type === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => props.setType(option.value)}
                  className={`flex h-12 items-center justify-center gap-2 rounded-md border text-sm font-bold transition ${
                    active
                      ? "border-ink bg-ink text-white"
                      : "border-line bg-white text-graphite hover:border-ink/40 hover:text-ink"
                  }`}
                  title={option.label}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {option.label}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="text-xs font-bold uppercase tracking-wide text-graphite">Content</p>
            <p className="text-xs font-semibold text-slate-500">{charCount.toLocaleString()} chars</p>
          </div>
          <textarea
            value={props.content}
            onChange={(event) => props.setContent(event.target.value)}
            className="min-h-72 w-full resize-y rounded-md border border-line bg-paper/70 p-4 text-base leading-7 text-ink outline-none transition focus:border-sky focus:shadow-focus"
            placeholder={
              props.type === "url"
                ? "Paste a URL, headline, or article text..."
                : "Paste Bangla, English, Banglish, or OCR text..."
            }
          />
        </div>

        <div className="grid gap-3 md:grid-cols-[1fr_170px]">
          <label className="block">
            <span className="mb-2 block text-xs font-bold uppercase tracking-wide text-graphite">Source</span>
            <input
              value={props.sourceUrl}
              onChange={(event) => props.setSourceUrl(event.target.value)}
              className="h-11 w-full rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-sky focus:shadow-focus"
              placeholder="https://source.example"
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-xs font-bold uppercase tracking-wide text-graphite">Region</span>
            <select
              value={props.region}
              onChange={(event) => props.setRegion(event.target.value)}
              className="h-11 w-full rounded-md border border-line bg-white px-3 text-sm font-bold outline-none transition focus:border-sky focus:shadow-focus"
            >
              <option value="BD">Bangladesh</option>
              <option value="US">United States</option>
              <option value="GLOBAL">Global</option>
            </select>
          </label>
        </div>

        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-graphite">Analysis depth</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {modes.map((option) => {
              const Icon = option.icon;
              const active = props.mode === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => props.setMode(option.value)}
                  className={`flex h-11 items-center justify-center gap-2 rounded-md border text-sm font-bold transition ${
                    active
                      ? "border-sky bg-sky text-white"
                      : "border-line bg-white text-graphite hover:border-sky/50 hover:text-ink"
                  }`}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {option.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-line pt-5">
          <div className="hidden text-sm text-graphite sm:block">
            <span className="font-bold text-ink">{props.mode}</span> mode selected
          </div>
          <button
            type="button"
            disabled={!canSubmit}
            onClick={props.onSubmit}
            className="inline-flex h-12 min-w-40 items-center justify-center gap-2 rounded-md bg-ink px-5 text-sm font-bold text-white transition hover:bg-ink/90 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {props.loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
            Run Analysis
          </button>
        </div>
      </div>
    </section>
  );
}
