import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import {
  FileSpreadsheet, Search, ArrowUpDown, ArrowUp, ArrowDown,
  ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight,
  Maximize2, Minimize2, Download, Hash, Type, Calendar, CheckSquare,
  RefreshCw, AlertCircle, Filter
} from 'lucide-react';

interface Props {
  datasetId: string;
  filename?: string;
  initialLimit?: number;
  showControls?: boolean;
  onClose?: () => void;
  isModal?: boolean;
}

export const DatasetTablePreview: React.FC<Props> = ({
  datasetId,
  filename,
  initialLimit = 25,
  onClose,
  isModal = false,
}) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination & Filtering state
  const [limit, setLimit] = useState(initialLimit);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [sortCol, setSortCol] = useState<string | undefined>(undefined);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [isExpanded, setIsExpanded] = useState(false);

  const fetchPreview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.getDatasetPreview(
        datasetId,
        limit,
        offset,
        search || undefined,
        sortCol,
        sortDir
      );
      setData(res);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dataset preview');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPreview();
  }, [datasetId, limit, offset, search, sortCol, sortDir]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    setSearch(searchInput);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearch('');
    setOffset(0);
  };

  const handleSort = (column: string) => {
    if (sortCol === column) {
      if (sortDir === 'asc') {
        setSortDir('desc');
      } else {
        setSortCol(undefined);
        setSortDir('asc');
      }
    } else {
      setSortCol(column);
      setSortDir('asc');
    }
    setOffset(0);
  };

  const totalRows = data?.total_rows || 0;
  const totalPages = Math.ceil(totalRows / limit) || 1;
  const currentPage = Math.floor(offset / limit) + 1;

  const handleExportCSV = () => {
    if (!data || !data.rows || data.rows.length === 0) return;
    const cols = data.columns;
    const csvContent = [
      cols.join(','),
      ...data.rows.map((row: any) =>
        cols.map((col: string) => {
          const val = row[col];
          if (val === null || val === undefined) return '';
          const str = String(val);
          return str.includes(',') || str.includes('"') || str.includes('\n')
            ? `"${str.replace(/"/g, '""')}"`
            : str;
        }).join(',')
      ),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename || data.filename || 'dataset'}_preview.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getTypeIcon = (dtype: string) => {
    const d = (dtype || '').toLowerCase();
    if (d.includes('int') || d.includes('float') || d.includes('num')) {
      return <span title="Numeric"><Hash className="w-3 h-3 text-sky-400 shrink-0" /></span>;
    }
    if (d.includes('date') || d.includes('time')) {
      return <span title="Date/Time"><Calendar className="w-3 h-3 text-amber-400 shrink-0" /></span>;
    }
    if (d.includes('bool')) {
      return <span title="Boolean"><CheckSquare className="w-3 h-3 text-emerald-400 shrink-0" /></span>;
    }
    return <span title="Text / Categorical"><Type className="w-3 h-3 text-purple-400 shrink-0" /></span>;
  };

  const containerClasses = isExpanded
    ? 'fixed inset-4 z-50 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden backdrop-blur-xl animate-in zoom-in-95'
    : 'bg-slate-900 border border-slate-800 rounded-2xl shadow-xl flex flex-col overflow-hidden';

  return (
    <div className={containerClasses}>
      {/* Top Header Bar */}
      <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
            <FileSpreadsheet className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                {filename || data?.filename || 'CSV Data Preview'}
              </h3>
              {data && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono border border-slate-700">
                  {totalRows.toLocaleString()} rows × {data.total_columns} cols
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400">
              Interactive spreadsheet head & data grid with instant search and sorting
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Search Form */}
          <form onSubmit={handleSearchSubmit} className="relative flex items-center">
            <input
              type="text"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              placeholder="Search table..."
              className="bg-slate-900 border border-slate-700/80 text-slate-200 text-xs rounded-lg pl-7 pr-7 py-1.5 focus:outline-none focus:border-sky-500 w-36 sm:w-48 placeholder-slate-500 transition-all"
            />
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2 pointer-events-none" />
            {searchInput && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="absolute right-2 text-slate-400 hover:text-slate-200 text-xs"
              >
                ×
              </button>
            )}
          </form>

          {/* Export CSV Button */}
          <button
            onClick={handleExportCSV}
            title="Download CSV preview"
            className="p-1.5 text-slate-300 bg-slate-800/80 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs flex items-center gap-1 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline text-[11px]">Export</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={fetchPreview}
            disabled={loading}
            title="Refresh preview"
            className="p-1.5 text-slate-300 bg-slate-800/80 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {/* Fullscreen Toggle */}
          {!isModal && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              title={isExpanded ? 'Minimize' : 'Maximize Fullscreen'}
              className="p-1.5 text-slate-300 bg-slate-800/80 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs transition-colors"
            >
              {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
          )}

          {/* Close if in modal */}
          {onClose && (
            <button
              onClick={onClose}
              className="px-2.5 py-1 text-xs text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700"
            >
              Close
            </button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-3 m-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Table Container */}
      <div className={`relative overflow-auto ${isExpanded ? 'flex-1 max-h-none' : 'max-h-[480px]'}`}>
        {loading && !data && (
          <div className="p-12 text-center text-slate-400 space-y-2">
            <RefreshCw className="w-6 h-6 animate-spin text-sky-400 mx-auto" />
            <p className="text-xs font-mono">Loading spreadsheet data...</p>
          </div>
        )}

        {data && data.rows && data.rows.length === 0 ? (
          <div className="p-10 text-center text-slate-400 space-y-2">
            <Filter className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs font-medium text-slate-300">No rows matched your search.</p>
            <p className="text-[11px] text-slate-500">Try adjusting or clearing your search term.</p>
          </div>
        ) : data && data.columns ? (
          <table className="w-full text-left text-xs border-collapse">
            {/* Sticky Column Headers */}
            <thead className="bg-slate-950 sticky top-0 z-20 shadow-sm border-b border-slate-800">
              <tr>
                {/* Row Number Column Header */}
                <th className="w-12 px-3 py-2.5 font-mono text-[11px] text-slate-500 bg-slate-950 border-r border-slate-800/80 text-center select-none">
                  #
                </th>
                {data.columns.map((col: string) => {
                  const dtype = data.dtypes ? data.dtypes[col] : '';
                  const isSorted = sortCol === col;
                  return (
                    <th
                      key={col}
                      onClick={() => handleSort(col)}
                      className="px-3.5 py-2.5 font-semibold text-slate-200 hover:bg-slate-800/60 cursor-pointer transition-colors border-r border-slate-800/80 select-none whitespace-nowrap group"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5">
                          {getTypeIcon(dtype)}
                          <span className="font-mono text-xs">{col}</span>
                        </div>
                        <div className="text-slate-500 group-hover:text-slate-300">
                          {isSorted ? (
                            sortDir === 'asc' ? (
                              <ArrowUp className="w-3 h-3 text-sky-400" />
                            ) : (
                              <ArrowDown className="w-3 h-3 text-sky-400" />
                            )
                          ) : (
                            <ArrowUpDown className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                          )}
                        </div>
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>

            {/* Table Rows */}
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs bg-slate-900/40">
              {data.rows.map((row: any, rIdx: number) => {
                const rowNumber = offset + rIdx + 1;
                return (
                  <tr
                    key={rIdx}
                    className="hover:bg-sky-500/[0.04] transition-colors group"
                  >
                    {/* Sticky Row Index */}
                    <td className="px-3 py-2 text-center text-[10px] text-slate-500 bg-slate-950/60 border-r border-slate-800/80 select-none font-mono">
                      {rowNumber}
                    </td>

                    {/* Column Cells */}
                    {data.columns.map((col: string) => {
                      const val = row[col];
                      const isNull = val === null || val === undefined;
                      const isNum = typeof val === 'number';

                      return (
                        <td
                          key={col}
                          className={`px-3.5 py-2 border-r border-slate-800/50 truncate max-w-xs ${
                            isNull
                              ? 'text-slate-600 italic text-[11px]'
                              : isNum
                              ? 'text-sky-300'
                              : 'text-slate-200'
                          }`}
                          title={isNull ? 'null / NaN' : String(val)}
                        >
                          {isNull ? 'null' : String(val)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : null}
      </div>

      {/* Bottom Pagination & Summary Footer */}
      {data && (
        <div className="p-3 bg-slate-950/90 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <span>
              Showing <strong className="text-slate-200 font-mono">{offset + 1}</strong> to{' '}
              <strong className="text-slate-200 font-mono">
                {Math.min(offset + limit, totalRows)}
              </strong>{' '}
              of <strong className="text-slate-200 font-mono">{totalRows.toLocaleString()}</strong> rows
            </span>

            {/* Rows Per Page Dropdown */}
            <div className="flex items-center gap-1.5 pl-2 border-l border-slate-800">
              <span className="text-[11px]">Rows:</span>
              <select
                value={limit}
                onChange={e => {
                  setLimit(Number(e.target.value));
                  setOffset(0);
                }}
                className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-2 py-0.5 text-xs focus:outline-none cursor-pointer"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>

          {/* Pagination Buttons */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setOffset(0)}
              disabled={currentPage <= 1 || loading}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 disabled:pointer-events-none transition-colors"
              title="First Page"
            >
              <ChevronsLeft className="w-3.5 h-3.5 text-slate-300" />
            </button>
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={currentPage <= 1 || loading}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 disabled:pointer-events-none transition-colors"
              title="Previous Page"
            >
              <ChevronLeft className="w-3.5 h-3.5 text-slate-300" />
            </button>

            <span className="px-3 py-1 font-mono text-xs text-slate-300">
              Page {currentPage} of {totalPages}
            </span>

            <button
              onClick={() => setOffset(offset + limit)}
              disabled={currentPage >= totalPages || loading}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 disabled:pointer-events-none transition-colors"
              title="Next Page"
            >
              <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            </button>
            <button
              onClick={() => setOffset((totalPages - 1) * limit)}
              disabled={currentPage >= totalPages || loading}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 disabled:pointer-events-none transition-colors"
              title="Last Page"
            >
              <ChevronsRight className="w-3.5 h-3.5 text-slate-300" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
