import React, { useState } from 'react';
import { Dataset } from '../types/dataset';
import { formatBytes, formatDate } from '../utils/formatters';
import { FileSpreadsheet, Trash2, Eye, RefreshCw, AlertCircle, Table, Sparkles } from 'lucide-react';
import { ConfirmModal } from './ConfirmModal';
import { DatasetTablePreview } from './DatasetTablePreview';
import { AIAutoPilotModal } from './AIAutoPilotModal';
import { useNavigate } from 'react-router-dom';

interface Props {
  datasets: Dataset[];
  loading: boolean;
  onRefresh: () => void;
  onDelete: (id: string) => Promise<void>;
}

export const DatasetList: React.FC<Props> = ({ datasets, loading, onRefresh, onDelete }) => {
  const navigate = useNavigate();
  const [selectedForDelete, setSelectedForDelete] = useState<Dataset | null>(null);
  const [previewDataset, setPreviewDataset] = useState<Dataset | null>(null);
  const [autoPilotDataset, setAutoPilotDataset] = useState<Dataset | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleDeleteConfirm = async () => {
    if (!selectedForDelete) return;
    setIsDeleting(true);
    setActionError(null);
    try {
      await onDelete(selectedForDelete.id);
      setSelectedForDelete(null);
    } catch (err: any) {
      setActionError(err.message || 'Failed to delete dataset');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          Uploaded Datasets
          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-slate-800 text-slate-400">
            {datasets.length}
          </span>
        </h2>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors border border-slate-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {actionError && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        {datasets.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <FileSpreadsheet className="w-12 h-12 text-slate-600 mx-auto" />
            <p className="text-slate-400 text-sm font-medium">No datasets uploaded yet.</p>
            <p className="text-slate-500 text-xs">Upload a CSV or XLSX file above to get started.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-800/60 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3.5 font-medium">Filename</th>
                  <th className="px-6 py-3.5 font-medium">Type</th>
                  <th className="px-6 py-3.5 font-medium">Size</th>
                  <th className="px-6 py-3.5 font-medium">Uploaded Date</th>
                  <th className="px-6 py-3.5 font-medium">Status</th>
                  <th className="px-6 py-3.5 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {datasets.map((dataset) => (
                  <tr key={dataset.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-200 flex items-center gap-3">
                      <FileSpreadsheet className="w-5 h-5 text-sky-400 shrink-0" />
                      <span className="truncate max-w-xs">{dataset.original_filename}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-0.5 text-xs font-mono rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {dataset.file_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                      {formatBytes(dataset.file_size)}
                    </td>
                    <td className="px-6 py-4 text-slate-400 text-xs">
                      {formatDate(dataset.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {dataset.upload_status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right space-x-1.5">
                      <button
                        onClick={() => setAutoPilotDataset(dataset)}
                        className="p-1.5 text-purple-300 hover:text-purple-200 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg transition-all inline-flex items-center gap-1 text-xs font-semibold shadow-sm cursor-pointer"
                        title="Run AI Auto-Pilot"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                        <span className="hidden sm:inline">Auto-Pilot</span>
                      </button>
                      <button
                        onClick={() => setPreviewDataset(dataset)}
                        className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors inline-flex items-center gap-1 text-xs"
                        title="Quick CSV Preview"
                      >
                        <Table className="w-4 h-4" />
                        <span className="hidden sm:inline">Preview</span>
                      </button>
                      <button
                        onClick={() => navigate(`/datasets/${dataset.id}`)}
                        className="p-1.5 text-slate-400 hover:text-sky-400 hover:bg-sky-500/10 rounded-lg transition-colors inline-flex items-center gap-1 text-xs"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                        <span className="hidden sm:inline">Details</span>
                      </button>
                      <button
                        onClick={() => setSelectedForDelete(dataset)}
                        className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                        title="Delete Dataset"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick CSV Data Grid Preview Modal */}
      {previewDataset && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-6xl max-h-[90vh] flex flex-col">
            <DatasetTablePreview
              datasetId={previewDataset.id}
              filename={previewDataset.original_filename}
              initialLimit={25}
              isModal={true}
              onClose={() => setPreviewDataset(null)}
            />
          </div>
        </div>
      )}

      {/* AI Auto-Pilot Modal */}
      {autoPilotDataset && (
        <AIAutoPilotModal
          isOpen={!!autoPilotDataset}
          onClose={() => setAutoPilotDataset(null)}
          datasetId={autoPilotDataset.id}
          filename={autoPilotDataset.original_filename}
          initialTarget={autoPilotDataset.target_column || undefined}
        />
      )}

      <ConfirmModal
        isOpen={!!selectedForDelete}
        title="Delete Dataset"
        message={`Are you sure you want to delete '${selectedForDelete?.original_filename}'? This action will permanently delete the file and database metadata.`}
        confirmText={isDeleting ? 'Deleting...' : 'Delete'}
        isDanger={true}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setSelectedForDelete(null)}
      />
    </div>
  );
};

