import { create } from 'zustand';

export type FilterValue = string[] | { start: string; end: string } | { min?: number; max?: number } | number | string;

export interface FilterState {
  filters: Record<string, FilterValue>;
  sourceChart: string | null;
  applyFilter: (column: string, value: FilterValue, fromChartId?: string) => void;
  clearFilter: (column: string) => void;
  clearAll: () => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  filters: {},
  sourceChart: null,
  applyFilter: (column, value, fromChartId = 'x_filter') =>
    set((state) => ({
      filters: { ...state.filters, [column]: value },
      sourceChart: fromChartId,
    })),
  clearFilter: (column) =>
    set((state) => {
      const next = { ...state.filters };
      delete next[column];
      return { filters: next, sourceChart: null };
    }),
  clearAll: () => set({ filters: {}, sourceChart: null }),
}));
