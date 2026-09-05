import React, { useState, useRef } from 'react';
import { UploadCloud, FileSpreadsheet, CheckCircle2, AlertCircle, Loader2, Sparkles, Eye } from 'lucide-react';
import { Dataset } from '../types/dataset';
import { apiService } from '../services/api';
import { formatBytes } from '../utils/formatters';

import { DatasetTablePreview } from './DatasetTablePreview';
import { AIAutoPilotModal } from './AIAutoPilotModal';

interface Props {
  onUploadSuccess?: (dataset: Dataset) => void;
}

export const UploadZone: React.FC<Props> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [lastUploaded, setLastUploaded] = useState<Dataset | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showAutoPilot, setShowAutoPilot] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !['csv', 'xlsx', 'xls'].includes(ext)) {
      setError('Invalid file type. Only CSV and XLSX formats are allowed.');
      return;
    }

    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      setError('File size exceeds the maximum limit of 50 MB.');
      return;
    }

    setError(null);
    setUploading(true);

    try {
      const dataset = await apiService.uploadDataset(file);
      setLastUploaded(dataset);
      setShowPreview(true);
      if (onUploadSuccess) {
        onUploadSuccess(dataset);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to upload dataset.';
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  };

  return (
    <div className="w-full space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200 ${
          isDragging
            ? 'border-sky-400 bg-sky-500/10'
            : 'border-slate-700 bg-slate-900/60 hover:border-slate-500 hover:bg-slate-800/40'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv, .xlsx, .xls"
          onChange={handleInputChange}
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="p-4 rounded-full bg-slate-800/80 text-sky-400 border border-slate-700 shadow-inner">
            {uploading ? (
              <Loader2 className="w-8 h-8 animate-spin" />
            ) : (
              <UploadCloud className="w-8 h-8" />
            )}
          </div>
          <div>
            <h3 className="text-base font-medium text-slate-200">Upload Dataset</h3>
            <p className="text-sm text-slate-400 mt-1">
              Drag & Drop your file here, or{' '}
              <span className="text-sky-400 font-semibold underline underline-offset-2">browse</span>
            </p>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 text-xs font-mono text-slate-400 border border-slate-700/60">
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            CSV or XLSX (Max 50MB)
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {lastUploaded && !uploading && (
        <div className="space-y-3 animate-in fade-in duration-200">
          <div className="flex items-center justify-between p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-semibold text-emerald-300">Dataset uploaded successfully</p>
                <p className="text-xs text-emerald-400/80 mt-0.5">
                  {lastUploaded.original_filename} • {formatBytes(lastUploaded.file_size)} • Ready for preview & modeling
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-xs font-medium transition-colors"
              >
                <span className="inline-flex items-center gap-1"><Eye className="w-3.5 h-3.5" />{showPreview ? 'Hide preview' : 'Preview data'}</span>
              </button>
              <button
                onClick={() => setShowAutoPilot(true)}
                className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-md shadow-purple-500/20 transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Run AI Auto-Pilot</span>
              </button>
            </div>
          </div>

          {showPreview && (
            <div className="pt-2">
              <DatasetTablePreview
                datasetId={lastUploaded.id}
                filename={lastUploaded.original_filename}
                initialLimit={15}
              />
            </div>
          )}

          {/* AI Auto-Pilot Modal */}
          {showAutoPilot && (
            <AIAutoPilotModal
              isOpen={showAutoPilot}
              onClose={() => setShowAutoPilot(false)}
              datasetId={lastUploaded.id}
              filename={lastUploaded.original_filename}
            />
          )}
        </div>
      )}
    </div>
  );
};
