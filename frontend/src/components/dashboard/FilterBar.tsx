import React from 'react';
import { FilterControl, FilterSpec } from './FilterControl';
import { useFilterStore } from '@/store/filterStore';
import { RotateCcw, Sliders, Sparkles } from 'lucide-react';

export interface FilterBarProps {
  filters: FilterSpec[];
  datasetId?: string;
}

export const FilterBar: React.FC<FilterBarProps> = ({ filters = [] }) => {
  const { filters: activeFilters, applyFilter, clearFilter, clearAll } =
    useFilterStore();

  const activeCount = Object.keys(activeFilters).filter(
    (k) => activeFilters[k] !== undefined && activeFilters[k] !== null
  ).length;

  if (filters.length === 0 && activeCount === 0) {
    return null;
  }

  return (
    <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-3.5 shadow-xl backdrop-blur-md">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-2 pr-2 border-r border-slate-800">
            <Sliders className="w-4 h-4 text-sky-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Slicers
            </span>
          </div>

          {filters.map((f) => (
            <FilterControl
              key={f.column}
              spec={f}
              value={activeFilters[f.column]}
              onChange={(val) => applyFilter(f.column, val, 'filter_bar')}
              onClear={() => clearFilter(f.column)}
            />
          ))}
        </div>

        {activeCount > 0 && (
          <div className="flex items-center gap-2.5">
            <span className="text-xs text-sky-400 bg-sky-950/60 border border-sky-800/80 px-2.5 py-1 rounded-xl font-medium flex items-center gap-1.5">
              <Sparkles className="w-3 h-3" />
              {activeCount} active filter{activeCount > 1 ? 's' : ''}
            </span>
            <button
              onClick={clearAll}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-medium bg-slate-800/80 text-slate-300 hover:text-white hover:bg-red-900/40 border border-slate-700 transition-all"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Clear All</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
