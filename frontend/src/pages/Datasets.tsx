import React from 'react';
import { UploadZone } from '../components/UploadZone';
import { DatasetList } from '../components/DatasetList';
import { useDatasets } from '../hooks/useDatasets';

export const Datasets: React.FC = () => {
  const { datasets, loading, refresh, deleteDataset } = useDatasets();

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Dataset Management</h1>
        <p className="text-slate-400 text-sm mt-1">
          Upload and manage tabular datasets stored in the local file system
        </p>
      </div>

      <UploadZone onUploadSuccess={() => refresh()} />

      <DatasetList
        datasets={datasets}
        loading={loading}
        onRefresh={refresh}
        onDelete={deleteDataset}
      />
    </div>
  );
};
