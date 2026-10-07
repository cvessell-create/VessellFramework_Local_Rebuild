export const REPOSITORY = "cvessell-create/VessellFramework_Local_Rebuild";
export const WORKFLOW = "run-framework.yml";
export const OPERATIONS = {
  "validate-framework": "Validate the framework",
  "claim-correction-study": "Run the claim-correction case study",
  "static-capture-study": "Run the offline static-capture case study"
} as const;
export type Operation = keyof typeof OPERATIONS;
export type WorkflowRun = {
  id: number; title: string; status: string; conclusion: string | null;
  created_at: string; url: string; sha: string;
};
export function isOperation(value: unknown): value is Operation {
  return typeof value === "string" && Object.hasOwn(OPERATIONS, value);
}
