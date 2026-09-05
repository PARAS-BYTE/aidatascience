import React, { useState, useRef, useEffect } from 'react';
import { Filter, Calendar, ChevronDown, X, Check } from 'lucide-react';

export interface FilterSpec {
  column: string;
  title?: string;
  control: 'date_range' | 'multiselect_dropdown' | 'range_slider' | 'categorical_select';
  options?: string[];
  min?: number | string;
  max?: number | string;
}

export interface FilterControlProps {
  spec: FilterSpec;
  value: any;
  onChange: (val: any) => void;
  onClear: () => void;
}

export const FilterControl: React.FC<FilterControlProps> = ({
  spec,
  value,
  onChange,
  onClear,
}) => {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const title = spec.title || spec.column.replace(/_/g, ' ');

  // Close dropdown on click outside
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const isActive =
    value !== undefined &&
    value !== null &&
    (Array.isArray(value) ? value.length > 0 : true);

  // 1. Date Range Control
  if (spec.control === 'date_range') {
    const startVal = value?.start || '';
    const endVal = value?.end || '';
    return (
      <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 rounded-xl px-3 py-1.5 shadow-sm">
        <Calendar className="w-3.5 h-3.5 text-sky-400 shrink-0" />
        <span className="text-xs font-medium text-slate-300">{title}:</span>
        <input
          type="date"
          value={startVal}
          onChange={(e) => onChange({ start: e.target.value, end: endVal || e.target.value })}
          className="bg-slate-800/80 border border-slate-700 text-slate-200 text-xs rounded-md px-1.5 py-0.5 outline-none focus:border-sky-500"
        />
        <span className="text-xs text-slate-500">→</span>
        <input
          type="date"
          value={endVal}
          onChange={(e) => onChange({ start: startVal || e.target.value, end: e.target.value })}
          className="bg-slate-800/80 border border-slate-700 text-slate-200 text-xs rounded-md px-1.5 py-0.5 outline-none focus:border-sky-500"
        />
        {isActive && (
          <button onClick={onClear} className="text-slate-500 hover:text-slate-300">
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
    );
  }

  // 2. Range Slider Control
  if (spec.control === 'range_slider') {
    const minVal = spec.min !== undefined ? Number(spec.min) : 0;
    const maxVal = spec.max !== undefined ? Number(spec.max) : 100;
    const currMin = value?.min !== undefined ? Number(value.min) : minVal;
    const currMax = value?.max !== undefined ? Number(value.max) : maxVal;

    return (
      <div className="flex items-center gap-2.5 bg-slate-900/90 border border-slate-800 rounded-xl px-3 py-1.5 shadow-sm">
        <Calendar className="w-3.5 h-3.5 text-purple-400 shrink-0" />
        <span className="text-xs font-medium text-slate-300">{title}:</span>
        <input
          type="range"
          min={minVal}
          max={maxVal}
          value={currMax}
          onChange={(e) => onChange({ min: currMin, max: Number(e.target.value) })}
          className="w-24 h-1.5 bg-slate-700 rounded-lg accent-sky-400"
        />
        <span className="text-xs font-mono text-sky-400">≤{currMax}</span>
        {isActive && (
          <button onClick={onClear} className="text-slate-500 hover:text-slate-300">
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
    );
  }

  // 3. Multiselect Dropdown (Default)
  const options = spec.options || [];
  const selectedItems: string[] = Array.isArray(value)
    ? value
    : value
    ? [String(value)]
    : [];

  const toggleOption = (opt: string) => {
    if (selectedItems.includes(opt)) {
      const next = selectedItems.filter((x) => x !== opt);
      next.length > 0 ? onChange(next) : onClear();
    } else {
      onChange([...selectedItems, opt]);
    }
  };

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
          isActive
            ? 'bg-sky-900/40 border border-sky-500/60 text-sky-200 shadow-sm shadow-sky-500/10'
            : 'bg-slate-900/90 border border-slate-800 text-slate-300 hover:border-slate-700'
        }`}
      >
        <Filter className="w-3.5 h-3.5 text-sky-400" />
        <span>{title}</span>
        {isActive && (
          <span className="px-1.5 py-0.5 bg-sky-500 text-slate-950 rounded-full font-bold text-[10px]">
            {selectedItems.length}
          </span>
        )}
        <ChevronDown className="w-3 h-3 text-slate-500" />
      </button>

      {open && (
        <div className="absolute top-full mt-1.5 left-0 z-50 w-56 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-2 space-y-1 max-h-60 overflow-y-auto">
          <div className="flex items-center justify-between px-2 py-1 border-b border-slate-800/80">
            <span className="text-xs font-semibold text-slate-400">Filter {title}</span>
            {isActive && (
              <button
                onClick={onClear}
                className="text-[11px] text-sky-400 hover:underline"
              >
                Reset
              </button>
            )}
          </div>
          {options.length > 0 ? (
            options.map((opt) => {
              const isSelected = selectedItems.includes(opt);
              return (
                <button
                  key={opt}
                  onClick={() => toggleOption(opt)}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                    isSelected ? 'bg-sky-500/20 text-sky-200' : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  <span className="truncate">{opt}</span>
                  {isSelected && <Check className="w-3.5 h-3.5 text-sky-400 shrink-0" />}
                </button>
              );
            })
          ) : (
            <p className="text-xs text-slate-500 px-2 py-2">No options</p>
          )}
        </div>
      )}
    </div>
  );
};

