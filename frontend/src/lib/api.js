// Minimal API helper for the CampusLearn AI frontend.
// Uses same-origin relative paths so the app works locally and behind the
// single public tunnel (the Vite dev proxy forwards /api to the backend).

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

const TOKEN_KEY = 'campuslearn_token';

// "Remember me": when false the token only lives in sessionStorage and is
// dropped when the browser closes; when true it persists in localStorage.
let rememberMe = true;

export function setRememberMe(value) {
  rememberMe = Boolean(value);
}

export function getToken() {
  return (
    localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || ''
  );
}

export function setToken(token) {
  if (!token) {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    return;
  }
  if (rememberMe) {
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.setItem(TOKEN_KEY, token);
  }
}

export async function apiFetch(path, { method = 'GET', body, auth = true, raw = false } = {}) {
  const headers = {};
  if (body !== undefined && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  if (auth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body:
      body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    const detail =
      (data && (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))) ||
      `Request failed (${res.status})`;
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }
  return raw ? data : data;
}

export async function chatRequest({ message, history = [], courseId = null }) {
  const payload = { message, history: history.slice(-20) };
  if (courseId) payload.course_id = courseId;
  return apiFetch('/api/chat', { method: 'POST', body: payload });
}

export async function loginRequest(email, password) {
  const data = await apiFetch('/api/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  });
  setToken(data.access_token);
  return data;
}

export async function registerRequest(name, email, password) {
  const data = await apiFetch('/api/auth/register', {
    method: 'POST',
    body: { name, email, password },
    auth: false,
  });
  return data;
}

export async function meRequest() {
  return apiFetch('/api/auth/me', { method: 'GET' });
}
export async function analyzePyqs({ courseId, numQuestions, answerLength, selectedMarks, fileIds } = {}) {
  const payload = {
    course_id: courseId || null,
    num_questions: numQuestions || 10,
    answer_length: answerLength || 'Medium',
    selected_marks: selectedMarks || null,
    file_ids: fileIds || null,
  };
  return apiFetch('/api/pyqs/analyze', { method: 'POST', body: payload });
}

export async function listMyCourses() {
  const data = await apiFetch('/api/courses/mine?page=1&page_size=100');
  return (data && data.items) || [];
}

export async function createCourse({ name, code, description }) {
  return apiFetch('/api/courses', {
    method: 'POST',
    body: { name, code, description },
  });
}

export const PYQ_MATERIAL_TYPE = 'pyq';

export async function uploadPyqPaper({ courseId, file }) {
  const ext = (file.name.match(/\.[^.]+$/) || [''])[0];
  const title = ext ? file.name.slice(0, -ext.length) : file.name;
  const form = new FormData();
  form.append('course_id', courseId);
  form.append('title', title || file.name);
  // Question papers are analysis-only: this type keeps them out of the RAG
  // index so they can never ground their own answers.
  form.append('material_type', PYQ_MATERIAL_TYPE);
  form.append('file', file);
  return apiFetch('/api/materials/upload', { method: 'POST', body: form });
}

function toSnakeCaseStyles(styles = {}) {
  const payload = {};
  for (const [key, value] of Object.entries(styles)) {
    if (value) {
      payload[key.replace(/([A-Z])/g, '_$1').toLowerCase()] = true;
    }
  }
  return payload;
}

function parseMarks(selectedMarks) {
  const value = parseInt(String(selectedMarks ?? '').replace(/[^0-9]/g, ''), 10);
  return Number.isFinite(value) && value > 0 ? value : null;
}

export async function generatePyqAnswer({ question, courseId, courseName, selectedMarks, answerLength, styles } = {}) {
  const stylePayload = toSnakeCaseStyles(styles);
  const payload = {
    question,
    course_id: courseId || null,
    course_name: courseName || null,
    marks: parseMarks(selectedMarks),
    answer_format: answerLength || 'Short',
    styles: Object.keys(stylePayload).length ? stylePayload : null,
  };
  return apiFetch('/api/pyqs/answer', { method: 'POST', body: payload });
}
