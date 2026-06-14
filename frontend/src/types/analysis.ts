export type InputType = "text" | "url" | "image" | "screenshot";
export type AnalysisMode = "quick" | "standard" | "deep" | "offline";
export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface EvidenceItem {
  label: string;
  evidence: string;
  signal_type: string;
  confidence: number;
}

export interface HighlightSpan {
  text: string;
  type: string;
  severity: RiskLevel;
}

export interface ScoreBreakdown {
  source_credibility: number;
  evidence_consistency: number;
  manipulation_intensity: number;
  language_patterns: number;
  context_risk: number;
  visual_authenticity: number;
  viral_risk: number;
}

export interface AgentFinding {
  agent: string;
  score: number;
  summary: string;
  evidence: EvidenceItem[];
}

export interface RiskFactor {
  label: string;
  score: number;
  impact: RiskLevel;
  explanation: string;
}

export interface ClaimCheck {
  claim: string;
  verdict: "supported" | "unsupported" | "uncertain" | "needs_external_verification";
  confidence: number;
  evidence: string;
  missing_evidence: string;
}

export interface TimelineEvent {
  stage: string;
  status: string;
  note: string;
}

export interface AnalysisResponse {
  analysis_id: string;
  schema_version: string;
  input_type: InputType;
  topic: string;
  language: string;
  trust_score: number;
  risk_level: RiskLevel;
  confidence: number;
  misinformation_probability: number;
  manipulation_score: number;
  source_score: number;
  evidence_quality: number;
  score_breakdown: ScoreBreakdown;
  reasoning: EvidenceItem[];
  highlight_spans: HighlightSpan[];
  agent_findings: AgentFinding[];
  visual_authenticity: {
    deepfake_risk: number;
    tampering_risk: number;
    notes: string;
  };
  risk_factors: RiskFactor[];
  claim_checks: ClaimCheck[];
  manipulation_patterns: string[];
  ai_generated_likelihood: number;
  viral_risk: number;
  regional_context: {
    region: string;
    sensitivity: number;
    note: string;
  };
  community_signal: {
    report_count: number;
    consensus: string;
    note: string;
  };
  trust_timeline: TimelineEvent[];
  expert_notes: string[];
  recommended_action: string;
  summary: string;
  uncertainty: string;
  moderation: {
    flagged: boolean;
    categories: string[];
    reason?: string | null;
  };
  cost: {
    model_used: string;
    input_tokens: number;
    output_tokens: number;
    cached_tokens: number;
    analysis_mode: AnalysisMode;
    cache_hit: boolean;
    openai_used: boolean;
  };
  source_url?: string | null;
  region: string;
  evidence_vs_inference: EvidenceItem[];
  raw_signals: Record<string, unknown>;
}

export interface ExplainResponse {
  analysis_id: string;
  answer: string;
  openai_used: boolean;
  model_used: string;
}
