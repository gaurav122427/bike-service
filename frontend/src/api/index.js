import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 15000,
});

// Attach JWT token from localStorage to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("kwick_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("kwick_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const getDashboard = () => api.get("/dashboard");
export const addService = (data) => api.post("/add-service", data);
export const getBikeHistory = (bikeNumber) =>
  api.get(`/bike/${encodeURIComponent(bikeNumber)}`);
export const getServices = (month, year) =>
  api.get("/services", { params: month && year ? { month, year } : {} });

export const downloadCsv = async () => {
  const res = await api.get("/export-csv", { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = "bike_services.csv";
  a.click();
  URL.revokeObjectURL(url);
};

export default api;
