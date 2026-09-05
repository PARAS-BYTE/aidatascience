export function applyPatch(spec: any, patch: any) {
  if (!spec || !patch) return spec;
  switch (patch.op) {
    case 'update_chart':
      return {
        ...spec,
        primary_chart:
          spec.primary_chart?.id === patch.chart_id
            ? { ...spec.primary_chart, ...patch.changes }
            : spec.primary_chart,
        secondary_charts: (spec.secondary_charts || []).map((c: any) =>
          c.id === patch.chart_id ? { ...c, ...patch.changes } : c
        ),
        charts: (spec.charts || []).map((c: any) =>
          c.id === patch.chart_id ? { ...c, ...patch.changes } : c
        ),
      };
    case 'add_chart':
      return {
        ...spec,
        secondary_charts: [...(spec.secondary_charts || []), patch.chart],
        charts: [...(spec.charts || []), patch.chart],
      };
    case 'remove_chart':
      return {
        ...spec,
        secondary_charts: (spec.secondary_charts || []).filter((c: any) => c.id !== patch.chart_id),
        charts: (spec.charts || []).filter((c: any) => c.id !== patch.chart_id),
      };
    case 'add_filter':
      return { ...spec, filters: [...(spec.filters || []), patch.filter] };
    default:
      return spec;
  }
}
