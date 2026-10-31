-- ========================================================
-- AI CRIME SCENE DETECTION & FORENSIC INTELLIGENCE SCHEMA
-- Supabase PostgreSQL Migration
-- ========================================================

-- 1. Cases Table
CREATE TABLE IF NOT EXISTS public.cases (
    case_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    investigator TEXT DEFAULT 'Forensic Officer',
    department TEXT DEFAULT 'Crime Scene Investigation Unit',
    location TEXT DEFAULT 'Unspecified Scene',
    incident_type TEXT DEFAULT 'Homicide / Scene Analysis',
    notes TEXT DEFAULT '',
    threat_level TEXT DEFAULT 'LOW',
    threat_score INTEGER DEFAULT 0,
    scene_narrative TEXT DEFAULT '',
    model_used TEXT NOT NULL,
    image_path TEXT NOT NULL,
    annotated_path TEXT NOT NULL,
    media_type TEXT DEFAULT 'image',
    video_duration REAL DEFAULT 0.0,
    clarity_score REAL DEFAULT 0.0,
    enhanced_path TEXT DEFAULT '',
    user_id INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Evidence Items Table
CREATE TABLE IF NOT EXISTS public.evidence_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES public.cases (case_id) ON DELETE CASCADE,
    class_name TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence REAL NOT NULL,
    activity TEXT DEFAULT '',
    bbox_x1 REAL NOT NULL,
    bbox_y1 REAL NOT NULL,
    bbox_x2 REAL NOT NULL,
    bbox_y2 REAL NOT NULL,
    crop_path TEXT DEFAULT '',
    video_timestamp REAL DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Audit Logs Table
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id TEXT,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Forensic Users Table
CREATE TABLE IF NOT EXISTS public.users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    fullname TEXT NOT NULL,
    badge TEXT DEFAULT '',
    unit TEXT DEFAULT 'Crime Scene Investigation Unit',
    role TEXT DEFAULT 'Forensic Investigator',
    email_verified INTEGER DEFAULT 0,
    verification_token TEXT DEFAULT '',
    reset_token TEXT DEFAULT '',
    reset_token_expires TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Analytics Events Table
CREATE TABLE IF NOT EXISTS public.analytics_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}'::jsonb,
    ip_hash TEXT DEFAULT '',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================================
-- INDEXES
-- ========================================================
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON public.cases(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_threat_level ON public.cases(threat_level);
CREATE INDEX IF NOT EXISTS idx_evidence_case_id ON public.evidence_items(case_id);
CREATE INDEX IF NOT EXISTS idx_evidence_activity ON public.evidence_items(activity);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON public.audit_logs(timestamp DESC);

-- ========================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ========================================================
ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;

-- Cases Policies
CREATE POLICY "Allow public read access to cases" ON public.cases FOR SELECT USING (true);
CREATE POLICY "Allow public insert access to cases" ON public.cases FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update access to cases" ON public.cases FOR UPDATE USING (true);
CREATE POLICY "Allow public delete access to cases" ON public.cases FOR DELETE USING (true);

-- Evidence Items Policies
CREATE POLICY "Allow public read access to evidence_items" ON public.evidence_items FOR SELECT USING (true);
CREATE POLICY "Allow public insert access to evidence_items" ON public.evidence_items FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public delete access to evidence_items" ON public.evidence_items FOR DELETE USING (true);

-- Audit Logs Policies
CREATE POLICY "Allow public read access to audit_logs" ON public.audit_logs FOR SELECT USING (true);
CREATE POLICY "Allow public insert access to audit_logs" ON public.audit_logs FOR INSERT WITH CHECK (true);

-- Users Policies
CREATE POLICY "Allow public read access to users" ON public.users FOR SELECT USING (true);
CREATE POLICY "Allow public insert access to users" ON public.users FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update access to users" ON public.users FOR UPDATE USING (true);

-- Analytics Events Policies
CREATE POLICY "Allow public access to analytics_events" ON public.analytics_events FOR ALL USING (true);
