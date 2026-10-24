/** A detached editable draft; identifiers, timestamps and results never enter it. */
export function copyExperimentDraft(source: {
  model_name: string; parameters: Record<string, unknown>; notes: string | null
}) {
  return {
    experiment_no: '',
    model_name: source.model_name,
    parameters: JSON.stringify(source.parameters, null, 2),
    notes: source.notes ?? '',
  }
}
