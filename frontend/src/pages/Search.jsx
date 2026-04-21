import { useState, useRef } from "react";
import { getBikeHistory } from "../api";
import { format } from "date-fns";

export default function Search() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef();

  const handleSearch = async (e) => {
    e.preventDefault();
    const q = query.trim().toUpperCase();
    if (!q) return;
    setLoading(true);
    setResult(null);
    setNotFound(false);
    setError(null);
    try {
      const { data } = await getBikeHistory(q);
      setResult(data);
    } catch (err) {
      if (err.response?.status === 404) {
        setNotFound(true);
      } else {
        setError("Search failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setQuery("");
    setResult(null);
    setNotFound(false);
    setError(null);
    inputRef.current?.focus();
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Search Bike</h1>
        <p className="text-sm text-gray-500 mt-0.5">Look up service history by bike registration number</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="card">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter bike number (e.g. MH12AB1234)"
              className="input-field pl-9 uppercase"
            />
          </div>
          <button type="submit" disabled={loading || !query.trim()} className="btn-primary px-5">
            {loading ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : "Search"}
          </button>
          {(result || notFound) && (
            <button type="button" onClick={handleClear} className="btn-secondary">Clear</button>
          )}
        </div>
      </form>

      {/* Not found */}
      {notFound && (
        <div className="card text-center py-10">
          <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="font-semibold text-gray-700">No bike found</p>
          <p className="text-sm text-gray-400 mt-1">Bike number <strong>{query.toUpperCase()}</strong> is not in the system.</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">{error}</div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Customer & Bike Summary */}
          <div className="card">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Customer</p>
                  <p className="text-lg font-bold text-gray-900">{result.customer_name}</p>
                  <p className="text-sm text-gray-500">{result.phone}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Bike</p>
                  <p className="font-semibold text-gray-800">{result.bike_number}</p>
                  <p className="text-sm text-gray-500">{result.bike_model}</p>
                </div>
              </div>
              <div className="bg-blue-50 border border-blue-100 rounded-xl px-6 py-4 text-center">
                <p className="text-3xl font-bold text-blue-600">{result.total_visits}</p>
                <p className="text-xs text-blue-500 font-medium mt-0.5">Total Visits</p>
              </div>
            </div>
          </div>

          {/* Service History */}
          <div className="card">
            <h3 className="text-base font-semibold text-gray-800 mb-4">
              Service History
              <span className="ml-2 text-xs font-normal text-gray-400">({result.service_history.length} records)</span>
            </h3>
            {result.service_history.length === 0 ? (
              <p className="text-gray-400 text-sm text-center py-6">No service records found.</p>
            ) : (
              <div className="space-y-3">
                {result.service_history.map((s, i) => (
                  <div key={s.id} className="flex gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                    <div className="w-7 h-7 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold">
                      {result.service_history.length - i}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                        <p className="text-sm font-semibold text-gray-800">
                          {format(new Date(s.service_date), "dd MMM yyyy")}
                        </p>
                        <span className="text-sm font-bold text-green-600">₹{s.cost.toLocaleString("en-IN")}</span>
                      </div>
                      <p className="text-sm text-gray-600">{s.service_details}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
