export type DecisionEnum =
  | "allow"
  | "monitor"
  | "rate_limit"
  | "challenge"
  | "block"
  | "would_block";

export type ThreatTypeEnum =
  | "benign"
  | "sql_injection"
  | "xss"
  | "path_traversal"
  | "command_injection"
  | "other_malicious";

export type SeverityEnum = "low" | "medium" | "high" | "critical";

export type SensitivityEnum = "low" | "medium" | "high" | "critical";

export type WAFModeEnum = "enforce" | "shadow";

export interface WAFInspectRequest {
  method: string;
  path: string;
  query: string;
  headers: Record<string, string>;
  body: string;
  source_ip: string;
  session_id?: string;
  user_id?: string;
}

export interface WAFInspectResponse {
  request_id: string;
  decision: DecisionEnum;
  risk_score: number;
  attack_type: ThreatTypeEnum | null;
  transformer_score: number | null;
  anomaly_score: number | null;
  session_score: number | null;
  application_score: number | null;
  rule_score: number | null;
  reasons: string[];
  signals: Record<string, number>;
  latency_ms: number;
}

export interface RequestEvent {
  id: number;
  request_id: string;
  timestamp: string;
  session_id: string | null;
  source_ip: string;
  user_id: string | null;
  method: string;
  path: string;
  query_string: string | null;
  status_code: number | null;
  latency_ms: number | null;
  transformer_score: number | null;
  anomaly_score: number | null;
  session_score: number | null;
  application_score: number | null;
  rule_score: number | null;
  final_risk_score: number;
  risk_score: number;
  attack_type: ThreatTypeEnum | null;
  decision: DecisionEnum;
  decision_reason: string | null;
  body_summary?: string;
}

export interface Session {
  id: number;
  session_key: string;
  source_ip: string;
  user_identifier: string | null;
  started_at: string;
  last_seen_at: string;
  request_count: number;
  anomaly_score: number;
  risk_score: number;
  current_state: string | null;
  endpoint_count: number;
  endpoint_sequence: Array<{
    endpoint: string;
    timestamp: string;
    risk: number;
    decision: DecisionEnum;
  }> | null;
  risk_timeline: Array<{
    timestamp: string;
    risk_score: number;
    decision: string;
  }> | null;
}

export interface EndpointProfile {
  id: number;
  path_template: string;
  method: string;
  expected_parameters: Record<string, any> | null;
  authentication_required: boolean;
  sensitivity_level: SensitivityEnum;
  allowed_content_types: string[] | null;
  request_count: number;
  baseline_stats: Record<string, any> | null;
}

export interface ThreatEvent {
  id: number;
  request_id: string;
  threat_type: ThreatTypeEnum;
  severity: SeverityEnum;
  confidence: number;
  risk_score: number;
  action: DecisionEnum;
  explanation: string | null;
  signals: Record<string, any> | null;
  created_at: string;
}

export interface AttackCampaign {
  id: number;
  session_id: string | null;
  source_ip: string;
  first_seen: string;
  last_seen: string;
  threat_count: number;
  campaign_score: number;
  status: string;
  threat_types: string[] | null;
  endpoints_targeted: string[] | null;
}

export interface PolicyThresholds {
  allow: number;
  monitor: number;
  rate_limit: number;
  challenge: number;
  block: number;
}

export interface PolicyWeights {
  transformer: number;
  anomaly: number;
  session: number;
  application: number;
  rules: number;
}

export interface Policy {
  mode: WAFModeEnum;
  thresholds: PolicyThresholds;
  weights: PolicyWeights;
}

export interface Explanation {
  request_id: string;
  decision: DecisionEnum;
  risk_score: number;
  attack_type: ThreatTypeEnum | null;
  summary: string;
  evidence: Array<{
    id: string;
    category: string;
    title: string;
    description: string;
    severity: string;
    score: number;
    raw_data: Record<string, any> | null;
  }>;
  signal_breakdown: Record<string, number>;
  policy_thresholds: Record<string, number>;
}

export interface AttackVariantResult {
  variant: string;
  original: string;
  transformations: string[];
  detected: boolean;
  risk_score: number;
  decision: DecisionEnum;
  attack_type: ThreatTypeEnum | null;
  latency_ms: number;
}

export interface AttackLabRunResponse {
  run_id: string;
  attack_family: string;
  total_variants: number;
  detected: number;
  missed: number;
  detection_rate: number;
  avg_latency_ms: number;
  variants: AttackVariantResult[];
  status?: string;
  started_at?: string;
}

export interface AttackFamily {
  id: string;
  name: string;
  description: string;
  default_payloads: string[];
}

export interface AttackLabRun {
  run_id: string;
  attack_family: string;
  total_variants: number;
  detected: number;
  missed: number;
  detection_rate: number;
  avg_latency_ms: number;
  status: string;
  started_at: string;
}

export interface BatchRunResponse {
  id: string;
  run_name: string;
  dataset_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  total_samples: number;
  results: Array<{
    index: number;
    request_id: string;
    method: string;
    path: string;
    risk_score: number;
    attack_type: ThreatTypeEnum | null;
    decision: DecisionEnum;
    latency_ms: number;
    ground_truth?: string;
  }> | null;
  f1?: number;
  precision?: number;
  recall?: number;
  false_positive_rate?: number;
}

export interface BatchResultItem {
  index: number;
  request_id: string;
  method: string;
  path: string;
  risk_score: number;
  attack_type: ThreatTypeEnum | null;
  decision: DecisionEnum;
  latency_ms: number;
  ground_truth?: string;
}

export interface BatchRun {
  run_id: string;
  dataset_name: string;
  total_samples: number;
  status: string;
  threats_detected: number;
  blocked: number;
  precision?: number;
  recall?: number;
  f1?: number;
  started_at: string;
}

export interface ModelInfo {
  id: number;
  name: string;
  version: string;
  artifact_path: string;
  training_dataset: string | null;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  validation_date: string | null;
  active: boolean;
  notes: string | null;
}

export interface EvaluationMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  false_positive_rate: number;
  per_class: Record<string, Record<string, number>>;
  confusion_matrix: number[][];
  latency_ms: number;
  throughput: number;
  known_attack_detection_rate: number | null;
  unseen_variant_detection_rate: number | null;
}

export interface EvaluationRunResponse {
  id: number;
  run_name: string;
  dataset_name: string;
  started_at: string;
  completed_at: string | null;
  total_samples: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  false_positive_rate: number | null;
  latency_ms: number | null;
  metrics: EvaluationMetrics | null;
}

export interface StatsSummary {
  total_requests: number;
  total_threats: number;
  total_blocked: number;
  recent_requests_1h: number;
  recent_threats_1h: number;
  avg_risk_score: number;
  trend_24h: Array<{
    hour: string;
    requests: number;
    threats: number;
  }>;
  attack_distribution: Record<string, number>;
  top_source_ips: Array<{ ip: string; count: number }>;
}

export interface HealthResponse {
  api: string;
  database: string;
  redis: string;
  model: string;
  version: string;
}