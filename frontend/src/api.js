import axios from 'axios';

const API = axios.create({ baseURL: '' });

export const analyzeCompany = (company_name) =>
  API.post('/api/analyze', { company_name });

export const compareCompanies = (company_names) =>
  API.post('/api/compare', { company_names });

export const getWatchlist = (email) =>
  API.get(`/api/watchlist/${email}`);

export const addToWatchlist = (company_id, user_email, alert_threshold = 10) =>
  API.post('/api/watchlist/add', { company_id, user_email, alert_threshold });

export const removeFromWatchlist = (company_id, user_email) =>
  API.delete(`/api/watchlist/remove?company_id=${company_id}&user_email=${user_email}`);

export const getAllCompanies = () =>
  API.get('/api/companies');

export const getPDFUrl = (company_id) =>
  `/api/report/${company_id}/pdf`;

export default API;
