import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Health Check
export const healthCheck = async () => {
  const response = await api.get("/health");
  return response.data;
};

// Single Resume Parsing
export const parseSingleResume = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/parse/single", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

// Parse Resume Text
export const parseResumeText = async (text, filename = null) => {
  const response = await api.post("/parse/text", null, {
    params: { text, filename },
  });
  return response.data;
};

// NER Entity Extraction
export const extractEntities = async (text) => {
  const response = await api.post("/ner/extract", null, {
    params: { text },
  });
  return response.data;
};

// Section Segmentation
export const segmentSections = async (
  file = null,
  text = null,
  filename = null
) => {
  const formData = new FormData();
  if (file) {
    formData.append("file", file);
  }

  const params = {};
  if (text) params.text = text;
  if (filename) params.filename = filename;

  const response = await api.post("/sections/segment", file ? formData : null, {
    params,
    headers: file ? { "Content-Type": "multipart/form-data" } : {},
  });
  return response.data;
};

// Contact Info Extraction
export const extractContactInfo = async (file = null, text = null) => {
  const formData = new FormData();
  if (file) {
    formData.append("file", file);
  }

  const params = {};
  if (text) params.text = text;

  const response = await api.post("/contact/extract", file ? formData : null, {
    params,
    headers: file ? { "Content-Type": "multipart/form-data" } : {},
  });
  return response.data;
};

// Batch Processing
export const batchParseResumes = async (files) => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await api.post("/batch/parse", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

// Get Batch Status
export const getBatchStatus = async (jobId) => {
  const response = await api.get(`/batch/status/${jobId}`);
  return response.data;
};

export default api;
