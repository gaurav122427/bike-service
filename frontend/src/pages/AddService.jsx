import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { addService } from "../api";
import { format } from "date-fns";

const initialForm = {
  customer_name: "",
  phone: "",
  bike_number: "",
  bike_model: "",
  chassis_number: "",
  service_date: format(new Date(), "yyyy-MM-dd'T'HH:mm"),
  odometer_km: "",
  service_details: "",
  cost: "",
  job_card: "",
  payment_mode: "",
  mechanic_incentive: "",
  incentive_paid: "",
};

export default function AddService() {
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.cost || isNaN(parseFloat(form.cost))) {
      setError("Please enter a valid cost.");
      return;
    }
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const payload = {
        ...form,
        cost: parseFloat(form.cost),
        service_date: new Date(form.service_date).toISOString(),
        odometer_km: form.odometer_km !== "" ? parseInt(form.odometer_km) : null,
        job_card: form.job_card === "" ? null : form.job_card === "true",
        mechanic_incentive: form.mechanic_incentive === "" ? null : form.mechanic_incentive === "true",
        chassis_number: form.chassis_number || null,
        incentive_paid: form.incentive_paid || null,
        payment_mode: form.payment_mode || null,
        bike_model: form.bike_model || null,
      };
      const { data } = await addService(payload);
      setResult(data);
      setForm(initialForm);
      setTimeout(() => {
        const d = new Date(form.service_date);
        navigate(`/services?month=${d.getMonth() + 1}&year=${d.getFullYear()}`);
      }, 1200);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add service. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Add Service</h1>
        <p className="text-sm text-gray-500 mt-0.5">Log a new bike service entry</p>
      </div>

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex gap-3">
          <svg className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <div>
            <p className="font-semibold text-green-800">Service recorded!</p>
            <p className="text-sm text-green-700 mt-0.5">
              {result.is_new_bike ? "New bike registered." : "Existing bike found."}{" "}
              Total visits: <strong>{result.visit_count}</strong>
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700 flex gap-2">
          <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card space-y-5">

        {/* Customer Info */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Customer Information</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Customer Name *</label>
              <input
                type="text"
                name="customer_name"
                value={form.customer_name}
                onChange={handleChange}
                required
                placeholder="John Doe"
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Mobile No.</label>
              <input
                type="tel"
                name="phone"
                value={form.phone}
                onChange={handleChange}
                placeholder="9876543210"
                className="input-field"
              />
            </div>
          </div>
        </div>

        {/* Bike Details */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Bike Details</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reg No. *</label>
              <input
                type="text"
                name="bike_number"
                value={form.bike_number}
                onChange={handleChange}
                required
                placeholder="MH12AB1234"
                className="input-field uppercase"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Bike Model</label>
              <input
                type="text"
                name="bike_model"
                value={form.bike_model}
                onChange={handleChange}
                placeholder="Honda Activa 6G"
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Chassis No.</label>
              <input
                type="text"
                name="chassis_number"
                value={form.chassis_number}
                onChange={handleChange}
                placeholder="ME4JF505XHT000000"
                className="input-field uppercase font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">K.M. (Odometer)</label>
              <input
                type="number"
                name="odometer_km"
                value={form.odometer_km}
                onChange={handleChange}
                min="0"
                placeholder="12500"
                className="input-field"
              />
            </div>
          </div>
        </div>

        {/* Service Details */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Service Details</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Service Date *</label>
              <input
                type="datetime-local"
                name="service_date"
                value={form.service_date}
                onChange={handleChange}
                required
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Amount (₹) *</label>
              <input
                type="number"
                name="cost"
                value={form.cost}
                onChange={handleChange}
                required
                min="0"
                step="0.01"
                placeholder="500"
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">J/C (Job Card)</label>
              <select name="job_card" value={form.job_card} onChange={handleChange} className="input-field">
                <option value="">— Select —</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Payment Mode</label>
              <select name="payment_mode" value={form.payment_mode} onChange={handleChange} className="input-field">
                <option value="">— Select —</option>
                <option value="Cash">Cash</option>
                <option value="Online">Online</option>
                <option value="Card">Card</option>
                <option value="Mixed">Mixed</option>
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Work Done *</label>
            <textarea
              name="service_details"
              value={form.service_details}
              onChange={handleChange}
              required
              rows={3}
              placeholder="Oil change, brake adjustment, chain lubrication..."
              className="input-field resize-none"
            />
          </div>
        </div>

        {/* Incentive */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Incentive</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Mechanic Incentive</label>
              <select name="mechanic_incentive" value={form.mechanic_incentive} onChange={handleChange} className="input-field">
                <option value="">— Select —</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Incentive Paid</label>
              <input
                type="text"
                name="incentive_paid"
                value={form.incentive_paid}
                onChange={handleChange}
                placeholder="e.g. 200"
                className="input-field"
              />
            </div>
          </div>
        </div>

        <div className="pt-1">
          <button type="submit" disabled={loading} className="btn-primary w-full sm:w-auto flex items-center justify-center gap-2">
            {loading ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}
            {loading ? "Saving..." : "Save Service"}
          </button>
        </div>
      </form>
    </div>
  );
}
