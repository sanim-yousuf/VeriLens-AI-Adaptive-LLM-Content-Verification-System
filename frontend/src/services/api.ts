import { AnalysisMode, AnalysisResponse, ExplainResponse, InputType } from "../types/analysis";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function createAnalysis(params: {
  type: InputType;
  content: string;
  analysis_mode: AnalysisMode;
  source_url?: string;
  region: string;
}): Promise<AnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/analyses`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      type: params.type,
      content: params.content,
      analysis_mode: params.analysis_mode,
      source_url: params.source_url || null,
      locale: params.region === "BD" ? "bn-BD" : "en-US",
      user_context: {
        region: params.region,
        audience: "general"
      }
    })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Analysis failed.");
  }

  return response.json();
}

export async function askReportQuestion(analysisId: string, question: string): Promise<ExplainResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/analyses/${analysisId}/explain`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ question })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Question failed.");
  }

  return response.json();
}
