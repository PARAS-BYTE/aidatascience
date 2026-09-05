import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Dataset } from '../types/dataset';
import { apiService } from '../services/api';
import { formatBytes, formatDate } from '../utils/formatters';
import { ArrowLeft, FileSpreadsheet, HardDrive, Calendar, CheckCircle2, Trash2, Sparkles, Bot, Zap } from 'lucide-react';
import { ConfirmModal } from '../components/ConfirmModal';
import { DatasetTablePreview } from '../components/DatasetTablePreview';
import { AIAutoPilotModal } from '../components/AIAutoPilotModal';

export const DatasetDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showAutoPilotModal, setShowAutoPilotModal] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchDetails = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiService.getDatasetById(id);
        setDataset(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Dataset not found');
      } finally {
        setLoading(false);
      }
    };
    fetchDetails();
  }, [id]);

  const handleDelete = async () => {
    if (!id) return;
    try {
      await apiService.deleteDataset(id);
      navigate('/datasets');
    } catch (err: any) {
      setError(err.message || 'Failed to delete dataset');
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-400">
        Loading dataset metadata...
      </div>
    );
  }

  if (error || !dataset) {
    return (
      <div className="space-y-4">
        <Link to="/datasets" className="inline-flex items-center gap-2 text-sm text-sky-400 hover:underline">
          <ArrowLeft className="w-4 h-4" /> Back to Datasets
        </Link>
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
          {error || 'Dataset not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <Link to="/datasets" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200">
            <ArrowLeft className="w-4 h-4" /> Back to Datasets
          </Link>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <FileSpreadsheet className="w-7 h-7 text-sky-400" />
            {dataset.original_filename}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAutoPilotModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-gradient-to-r from-purple-600 via-indigo-600 to-sky-600 hover:from-purple-500 hover:via-indigo-500 hover:to-sky-500 rounded-xl shadow-lg shadow-purple-500/20 transition-all cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            <span>Run AI Auto-Pilot</span>
          </button>
          <button
            onClick={() => setShowDeleteModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-xl transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Delete Dataset
          </button>
        </div>
      </div>

      {/* Autonomous AI Auto-Pilot Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-purple-950/60 via-slate-900 to-indigo-950/60 border border-purple-500/30 p-6 sm:p-8 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-300 text-xs font-semibold">
              <Bot className="w-3.5 h-3.5" />
              Autonomous Data Scientist
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              One-Click End-to-End AI Auto-Pilot
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              Autonomously profile features, formulate domain transformations (interactions, date decompositions),
              benchmark candidate ML architectures, and generate SHAP explainability diagnostics.
            </p>
          </div>
          <button
            onClick={() => setShowAutoPilotModal(true)}
            className="px-6 py-3.5 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-sm shadow-xl shadow-purple-500/25 transition-all flex items-center gap-2.5 shrink-0 cursor-pointer group"
          >
            <Sparkles className="w-4 h-4 group-hover:rotate-12 transition-transform" />
            <span>Launch Auto-Pilot</span>
            <Zap className="w-4 h-4 text-amber-300 group-hover:scale-110 transition-transform" />
          </button>
        </div>
      </div>

      {/* Metadata Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase">
            <HardDrive className="w-4 h-4 text-sky-400" /> File Size
          </div>
          <p className="text-xl font-bold text-slate-100 font-mono">
            {formatBytes(dataset.file_size)}
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase">
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" /> File Format
          </div>
          <p className="text-xl font-bold text-slate-100 font-mono">
            {dataset.file_type}
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase">
            <CheckCircle2 className="w-4 h-4 text-indigo-400" /> Upload Status
          </div>
          <p className="text-xl font-bold text-emerald-400 font-mono">
            {dataset.upload_status}
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase">
            <Calendar className="w-4 h-4 text-amber-400" /> Upload Date
          </div>
          <p className="text-sm font-medium text-slate-200">
            {formatDate(dataset.created_at)}
          </p>
        </div>
      </div>

      {/* Internal Metadata Details */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
        <h3 className="text-base font-semibold text-slate-200">Internal Storage Details</h3>
        <div className="space-y-3 font-mono text-xs">
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 flex flex-col md:flex-row justify-between gap-2">
            <span className="text-slate-400">Dataset UUID:</span>
            <span className="text-sky-400 select-all">{dataset.id}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 flex flex-col md:flex-row justify-between gap-2">
            <span className="text-slate-400">Stored Filename:</span>
            <span className="text-slate-200 select-all">{dataset.stored_filename}</span>
          </div>
        </div>
      </div>

      {/* Interactive Excel Data Table Preview */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-sky-400" />
          Spreadsheet Data Grid (Head Preview)
        </h2>
        <DatasetTablePreview
          datasetId={dataset.id}
          filename={dataset.original_filename}
          initialLimit={25}
        />
      </div>

      <ConfirmModal
        isOpen={showDeleteModal}
        title="Delete Dataset"
        message={`Are you sure you want to delete '${dataset.original_filename}'?`}
        confirmText="Delete"
        isDanger={true}
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteModal(false)}
      />

      {/* Autonomous AI Auto-Pilot Modal */}
      {showAutoPilotModal && (
        <AIAutoPilotModal
          isOpen={showAutoPilotModal}
          onClose={() => setShowAutoPilotModal(false)}
          datasetId={dataset.id}
          filename={dataset.original_filename}
          initialTarget={dataset.target_column || undefined}
        />
      )}
    </div>
  );
};
