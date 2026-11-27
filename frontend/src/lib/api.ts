import { supabase } from "./supabase";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function detailText(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  // Errores de validación de FastAPI: lista de { msg }
  if (Array.isArray(detail)) {
    const msgs = detail.map((d) => (typeof d === "object" && d !== null && "msg" in d ? String(d.msg).replace(/^Value error, /, "") : "")).filter(Boolean);
    if (msgs.length) return msgs.join(". ");
  }
  return fallback;
}

/** Llama a la API con el token de la sesión de Supabase. */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const { data } = await supabase().auth.getSession();
  const token = data.session?.access_token;
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body: { detail?: unknown } = await res.json();
      detail = detailText(body.detail, detail);
    } catch {
      // Respuesta sin JSON: se usa el texto de estado
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const post = <T>(path: string, body: unknown = {}) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });

/** Mensaje legible para mostrar en pantalla, tanto si la API respondió con error como si no respondió. */
export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return "No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.";
}

// ---------- tipos de la API ----------

export type Role = "admin" | "docente" | "estudiante";
export type CategoryKey = "entendio_mal" | "no_sabe" | "lo_domina" | "falta_practica";
export type Light = "verde" | "ambar" | "rojo" | "sin_datos";
export type ContentStatus = "generando" | "pendiente" | "aprobado" | "rechazado" | "reemplazado" | "error_ia" | "requiere_docente";
export const AREAS = ["Matemática", "Comunicación", "Ciencia y Tecnología", "Personal Social"] as const;

export interface AppUser {
  id: string;
  role: Role;
  full_name: string;
  email: string;
  username: string | null;
  active: boolean;
  must_change_password: boolean;
}

export interface Classroom {
  id: number;
  name: string;
  year: number;
  grade: number;
  section: string;
  teacher: { id: string; full_name: string } | null;
}

export interface Me {
  user: AppUser;
  student?: { id: number; code: string; classroom: Classroom; has_profile: boolean };
}

export interface StudentInfo {
  id: number;
  code: string;
  full_name: string;
  username: string;
  active: boolean;
  interests: string;
  classroom: { id: number; name: string; grade: number };
}

export interface Profile {
  level: "inicio" | "en_proceso" | "logrado" | "destacado";
  reading_level: string;
  pace: string;
  strengths: string[];
  gaps: string[];
  interests: string[];
  recommendation: string;
}

export interface Exercise {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
  expected_seconds: number;
}

export interface ContentBody {
  title: string;
  explanation: string;
  examples: string[];
  exercises: Exercise[];
  reinforcement_activity: string;
  adaptation_notes?: string;
}

export interface ContentSummary {
  id: number;
  student_id: number;
  student_name: string;
  classroom: string;
  kind: "material" | "prueba_inicial";
  area: string;
  topic: string;
  difficulty: number;
  status: ContentStatus;
  origin: string;
  title: string | null;
  returns_count: number;
  error: string;
  created_at: string;
  updated_at: string;
}

export interface ContentDetail extends ContentSummary {
  base: ContentBody | null;
  adapted: ContentBody | null;
  reviews: { decision: string; note: string; created_at: string }[];
}

export interface ReinforcementItem {
  id: number;
  student_id: number;
  student_name: string;
  classroom: string;
  topic: string;
  status: string;
  error: string;
  created_at: string;
  data: {
    suspected_misconception: string;
    activity_title: string;
    steps: string[];
    materials: string[];
    mistakes: { enunciado: string; respuesta: string; correcta: string; confianza: number }[];
  } | null;
}

export interface TopicSummary {
  topic: string;
  answers: number;
  accuracy: number;
  light: Light;
  avg_time_s: number;
  categories: Record<string, number>;
}

export interface EventRow {
  id: number;
  topic: string;
  question: string;
  answer: string;
  correct: boolean;
  time_ms: number;
  expected_ms: number;
  confidence: number;
  changes: number;
  environment: string;
  category: string;
  category_key: CategoryKey;
  created_at: string;
}

export interface ReportRow {
  id: number;
  status: "generando" | "listo" | "error_ia";
  error: string;
  created_at: string;
  automatic: boolean;
  data: { summary: string; progress: string[]; difficulties: string[]; recommendations: string[] } | null;
}

export interface StudentDetail {
  student: StudentInfo;
  profile: Profile | null;
  profile_history: { source: string; level: string; created_at: string }[];
  topics: TopicSummary[];
  contents: ContentSummary[];
  events: EventRow[];
  reports: ReportRow[];
}

export interface ProgressPoint {
  submission_id: number;
  date: string;
  topic: string;
  kind: string;
  difficulty: number;
  accuracy: number;
  avg_time_s: number;
  decision: string | null;
}

export interface Alert {
  type: "concepto" | "tiempo" | "indecision";
  student_id: number;
  student: string;
  topic: string;
  detail: string;
  created_at: string;
}

export interface ClassroomDashboard {
  classroom: Classroom;
  kpis: { students: number; answers: number; accuracy: number | null; avg_time_s: number | null; to_review: number };
  students: (StudentInfo & {
    has_profile: boolean;
    answers: number;
    accuracy: number | null;
    light: Light;
    topics: { topic: string; light: Light; accuracy: number }[];
    last_category: string | null;
  })[];
  alerts: Alert[];
  by_environment: Record<string, number>;
}

export interface AgentRunRow {
  id: number;
  agent: string;
  student_id: number | null;
  student_name: string | null;
  content_id: number | null;
  status: "ok" | "error";
  model: string;
  attempts: number;
  latency_ms: number;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: string;
  created_at: string;
}

export interface StudentMaterial {
  id: number;
  kind: "material" | "prueba_inicial";
  area: string;
  topic: string;
  difficulty: number;
  title: string;
  explanation: string;
  examples: string[];
  exercises: { index: number; question: string; options: string[] }[];
}

export interface StudentHome {
  name: string;
  classroom: string;
  has_profile: boolean;
  initial_tests: (Omit<StudentMaterial, "exercises"> & { completed: boolean; exercise_count: number })[];
  materials: (Omit<StudentMaterial, "exercises"> & { completed: boolean; exercise_count: number })[];
}

export interface SubmitResult {
  submission_id: number;
  results: { index: number; correct: boolean; category: string; category_key: CategoryKey; correct_option?: string; explanation?: string }[];
}

export interface SubmissionStatus {
  status: "procesando" | "listo" | "error_ia";
  feedback: { overall: string; items: { index: number; correct: boolean; error_type: string; message: string }[] } | null;
  has_next_material: boolean;
  decision: string | null;
}
