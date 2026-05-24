import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export function useProviders() {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProviders = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/providers');
      setProviders(res.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch providers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  return { providers, loading, error, refetch: fetchProviders };
}
