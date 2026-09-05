import { useState, useEffect, useCallback } from 'react';
import { Dataset } from '../types/dataset';
import { apiService } from '../services/api';

export function useDatasets() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getDatasets();
      setDatasets(data.items);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to fetch datasets';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const deleteDataset = async (id: string): Promise<void> => {
    try {
      await apiService.deleteDataset(id);
      setDatasets((prev) => prev.filter((d) => d.id !== id));
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to delete dataset';
      throw new Error(msg);
    }
  };

  return {
    datasets,
    loading,
    error,
    refresh: fetchDatasets,
    deleteDataset,
  };
}
