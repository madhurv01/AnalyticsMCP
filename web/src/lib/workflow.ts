export const WORKFLOW_STEPS: { key: string; label: string }[] = [
  { key: "dataset_loading", label: "Loading dataset" },
  { key: "schema_detection", label: "Detecting schema" },
  { key: "data_cleaning", label: "Cleaning data" },
  { key: "type_inference", label: "Inferring column types" },
  { key: "missing_value_analysis", label: "Analyzing missing values" },
  { key: "relationship_discovery", label: "Discovering relationships" },
  { key: "statistical_analysis", label: "Running statistical analysis" },
  { key: "anomaly_detection", label: "Detecting anomalies" },
  { key: "chart_generation", label: "Generating charts" },
  { key: "insight_extraction", label: "Extracting insights" },
  { key: "excel_report_creation", label: "Building Excel report" },
  { key: "final_export", label: "Finalizing export" },
];

export function stepIndex(key: string | null): number {
  if (!key) return -1;
  return WORKFLOW_STEPS.findIndex((s) => s.key === key);
}
