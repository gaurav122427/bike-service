import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { getServices, downloadCsv } from "../api";
import { format } from "date-fns";

const MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function parseMonthLabel(label) {
  const [mon, yr] = label.split(" ");
  return { month: MONTH_NAMES.indexOf(mon) + 1, year: parseInt(yr) };
}

const currency = (n) =>
  n != null ? `₹${Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 })}` : "—";

const Badge = ({ value, colorClass = "bg-gray-100 text-gray-600" }) =>
  value != null ? (
    <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded ${colorClass}`}>
      {String(value)}
    </span>
  ) : <span className="text-gray-300 text-xs">—</span>;

const PaymentBadge = ({ mode }) => {
  const map = {
    Online: "bg-blue-50 text-blue-700",
    Cash:   "bg-green-50 text-green-700",
    Card:   "bg-purple-50 text-purple-700",
    Mixed:  "bg-orange-50 text-orange-700",
  };
  return <Badge value={mode} colorClass={map[mode] || "bg-gray-100 text-gray-600"} />;
};

const BoolBadge = ({ value, trueLabel = "Yes", falseLabel = "No" }) => {
  if (value === null || value === undefined)
    return <span className="text-gray-300 text-xs">—</span>;
  return (
    <Badge
      value={value ? trueLabel : falseLabel}
      colorClass={value ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}
    />
  );
};

export default function Services() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [paymentFilter, setPaymentFilter] = useState("");
  const [incentiveFilter, setIncentiveFilter] = useState("");

  const selectedMonth = searchParams.get("month") ? parseInt(searchParams.get("month")) : null;
  const selectedYear  = searchParams.get("year")  ? parseInt(searchParams.get("year"))  : null;

  const load = useCallback(async (month, year) => {
    setLoading(true);
    setError(null);
    try {
      const { data: res } = await getServices(month, year);
      setData(res);
    } catch {
      setError("Failed to load services. Check the backend is running.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(selectedMonth, selectedYear); }, [load, selectedMonth, selectedYear]);

  const handleMonthChange = (e) => {
    const val = e.target.value;
    setSearchQuery("");
    setPaymentFilter("");
    setIncentiveFilter("");
    if (!val) {
      setSearchParams({});
    } else {
      const { month, year } = parseMonthLabel(val);
      setSearchParams({ month, year });
    }
  };

  const currentLabel =
    selectedMonth && selectedYear ? `${MONTH_NAMES[selectedMonth - 1]} ${selectedYear}` : "";

  // Client-side filters
  const q = searchQuery.trim().toLowerCase();
  const activeFilters = q || paymentFilter || incentiveFilter;
  const filteredServices = data?.services?.filter((s) => {
    if (q && !(
      s.bike_number?.toLowerCase().includes(q) ||
      s.customer_name?.toLowerCase().includes(q) ||
      s.phone?.includes(q) ||
      s.service_details?.toLowerCase().includes(q) ||
      s.chassis_number?.toLowerCase().includes(q) ||
      s.payment_mode?.toLowerCase().includes(q)
    )) return false;
    if (paymentFilter && s.payment_mode !== paymentFilter) return false;
    if (incentiveFilter !== "") {
      const want = incentiveFilter === "yes";
      if (s.mechanic_incentive !== want) return false;
    }
    return true;
  }) ?? [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Service Records</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data
              ? activeFilters
                ? `${filteredServices.length} of ${data.total_count} records`
                : selectedMonth
                  ? `${data.total_count} records · ${currentLabel}`
                  : `All ${data.total_count} records`
              : "Loading…"}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Search */}
          <div className="relative">
            <svg className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search name, reg, phone…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field pl-8 pr-8 py-2 text-sm min-w-[200px]"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
          {/* Payment filter */}
          <div className="relative">
            <select
              value={paymentFilter}
              onChange={(e) => setPaymentFilter(e.target.value)}
              className="input-field pr-8 py-2 text-sm appearance-none min-w-[140px]"
            >
              <option value="">All Payments</option>
              <option value="Cash">Cash</option>
              <option value="Online">Online</option>
              <option value="Card">Card</option>
              <option value="Mixed">Mixed</option>
              <option value="Unknown">Unknown</option>
            </select>
            <svg className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>

          {/* Incentive filter */}
          <div className="relative">
            <select
              value={incentiveFilter}
              onChange={(e) => setIncentiveFilter(e.target.value)}
              className="input-field pr-8 py-2 text-sm appearance-none min-w-[140px]"
            >
              <option value="">All Incentives</option>
              <option value="yes">Incentive: Yes</option>
              <option value="no">Incentive: No</option>
            </select>
            <svg className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>

          <div className="relative">
            <select
              value={currentLabel}
              onChange={handleMonthChange}
              className="input-field pr-8 py-2 text-sm appearance-none min-w-[160px]"
            >
              <option value="">All Months</option>
              {data?.available_months?.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
          <button onClick={downloadCsv} className="btn-secondary flex items-center gap-1.5 text-sm py-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export CSV
          </button>
        </div>
      </div>

      {/* Summary strip */}
      {data && !loading && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="card py-3">
            <p className="text-xs text-gray-500 font-medium">Total Records</p>
            <p className="text-2xl font-bold text-gray-900 mt-0.5">{data.total_count}</p>
          </div>
          <div className="card py-3">
            <p className="text-xs text-gray-500 font-medium">Total Revenue</p>
            <p className="text-2xl font-bold text-green-600 mt-0.5">{currency(data.total_revenue)}</p>
          </div>
          <div className="card py-3">
            <p className="text-xs text-gray-500 font-medium">Avg. Per Service</p>
            <p className="text-2xl font-bold text-blue-600 mt-0.5">
              {data.total_count > 0 ? currency(data.total_revenue / data.total_count) : "—"}
            </p>
          </div>
          <div className="card py-3">
            <p className="text-xs text-gray-500 font-medium">With Job Card</p>
            <p className="text-2xl font-bold text-purple-600 mt-0.5">
              {filteredServices.filter(s => s.job_card).length}
            </p>
          </div>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <div className="card text-center py-10">
          <p className="text-red-500 font-medium">{error}</p>
          <button onClick={() => load(selectedMonth, selectedYear)} className="btn-secondary mt-3 text-sm">Retry</button>
        </div>
      ) : data?.services?.length === 0 ? (
        <div className="card text-center py-16">
          <svg className="w-12 h-12 text-gray-200 mx-auto mb-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p className="font-semibold text-gray-600">No records found</p>
          <p className="text-sm text-gray-400 mt-1">
            {selectedMonth ? `No services recorded in ${currentLabel}.` : "No service records yet."}
          </p>
        </div>
      ) : (
        <>
          {/* ── Desktop Table ── */}
          <div className="card p-0 overflow-hidden hidden lg:block">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    {[
                      "#", "Date", "Reg No.", "Name", "Mobile No.",
                      "Chassis No.", "K.M.", "J/C", "Work Done",
                      "Amount", "Payment", "Incentive", "Incentive Paid"
                    ].map((h) => (
                      <th key={h} className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filteredServices.map((s, i) => (
                    <tr key={s.id} className="hover:bg-blue-50/30 transition-colors">
                      {/* # */}
                      <td className="px-3 py-2.5 text-gray-400">{i + 1}</td>

                      {/* Date */}
                      <td className="px-3 py-2.5 whitespace-nowrap text-gray-700">
                        {format(new Date(s.service_date), "dd MMM yy")}
                      </td>

                      {/* Reg No. */}
                      <td className="px-3 py-2.5">
                        <span className="bg-blue-50 text-blue-700 font-semibold px-2 py-0.5 rounded whitespace-nowrap">
                          {s.bike_number}
                        </span>
                      </td>

                      {/* Name */}
                      <td className="px-3 py-2.5 font-medium text-gray-800 whitespace-nowrap">
                        {s.customer_name}
                      </td>

                      {/* Mobile No. */}
                      <td className="px-3 py-2.5 text-gray-500 whitespace-nowrap">
                        {s.phone || "—"}
                      </td>

                      {/* Chassis No. */}
                      <td className="px-3 py-2.5 text-gray-500 whitespace-nowrap font-mono text-xs">
                        {s.chassis_number || <span className="text-gray-300">—</span>}
                      </td>

                      {/* K.M. */}
                      <td className="px-3 py-2.5 text-gray-600 whitespace-nowrap text-right">
                        {s.odometer_km != null ? s.odometer_km.toLocaleString("en-IN") : <span className="text-gray-300">—</span>}
                      </td>

                      {/* J/C */}
                      <td className="px-3 py-2.5">
                        <BoolBadge value={s.job_card} />
                      </td>

                      {/* Work Done */}
                      <td className="px-3 py-2.5 text-gray-700 max-w-xs">
                        <span className="line-clamp-2">{s.service_details}</span>
                      </td>

                      {/* Amount */}
                      <td className="px-3 py-2.5 font-semibold text-green-600 whitespace-nowrap text-right">
                        {currency(s.cost)}
                      </td>

                      {/* Payment */}
                      <td className="px-3 py-2.5">
                        <PaymentBadge mode={s.payment_mode} />
                      </td>

                      {/* Deepak Incentive */}
                      <td className="px-3 py-2.5">
                        <BoolBadge value={s.mechanic_incentive} />
                      </td>

                      {/* Incentive Paid */}
                      <td className="px-3 py-2.5 text-gray-500 whitespace-nowrap">
                        {s.incentive_paid || <span className="text-gray-300">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>

                {/* Footer total */}
                <tfoot>
                  <tr className="bg-gray-50 border-t-2 border-gray-200 font-semibold text-sm">
                    <td colSpan={9} className="px-3 py-3 text-gray-700">
                      Total ({filteredServices.length} records{activeFilters ? ` of ${data.total_count}` : ""})
                    </td>
                    <td className="px-3 py-3 text-green-700 text-right whitespace-nowrap">
                      {currency(filteredServices.reduce((sum, s) => sum + (s.cost || 0), 0))}
                    </td>
                    <td colSpan={3} />
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* ── Mobile Cards ── */}
          <div className="lg:hidden space-y-3">
            {filteredServices.map((s) => (
              <div key={s.id} className="card space-y-3">
                {/* Row 1: reg + date + amount */}
                <div className="flex items-start justify-between">
                  <div>
                    <span className="bg-blue-50 text-blue-700 font-semibold text-sm px-2 py-0.5 rounded">
                      {s.bike_number}
                    </span>
                    <p className="text-xs text-gray-400 mt-1">
                      {format(new Date(s.service_date), "dd MMM yyyy")}
                      {s.odometer_km != null && ` · ${s.odometer_km.toLocaleString("en-IN")} km`}
                    </p>
                  </div>
                  <p className="font-bold text-green-600">{currency(s.cost)}</p>
                </div>

                {/* Row 2: customer */}
                <div>
                  <p className="font-semibold text-gray-800">{s.customer_name}</p>
                  <p className="text-xs text-gray-400">{s.phone || "—"}</p>
                  {s.chassis_number && (
                    <p className="text-xs text-gray-400 font-mono mt-0.5">{s.chassis_number}</p>
                  )}
                </div>

                {/* Row 3: work done */}
                <p className="text-sm text-gray-700 border-t border-gray-50 pt-2">{s.service_details}</p>

                {/* Row 4: badges */}
                <div className="flex flex-wrap gap-1.5">
                  <PaymentBadge mode={s.payment_mode} />
                  {s.job_card != null && (
                    <Badge
                      value={`J/C: ${s.job_card ? "Yes" : "No"}`}
                      colorClass={s.job_card ? "bg-purple-50 text-purple-700" : "bg-gray-100 text-gray-500"}
                    />
                  )}
                  {s.mechanic_incentive != null && (
                    <Badge
                      value={`Incentive: ${s.mechanic_incentive ? "Yes" : "No"}`}
                      colorClass={s.mechanic_incentive ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}
                    />
                  )}
                  {s.incentive_paid && s.incentive_paid !== "—" && (
                    <Badge value={`Paid: ${s.incentive_paid}`} colorClass="bg-gray-100 text-gray-500" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
