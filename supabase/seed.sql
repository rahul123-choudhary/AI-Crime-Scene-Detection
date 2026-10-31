-- ========================================================
-- AI CRIME SCENE DETECTION - SEED DATA FOR SUPABASE
-- ========================================================

-- Seed Lead Forensic Officer
INSERT INTO public.users (
    email,
    username,
    password_hash,
    fullname,
    badge,
    unit,
    role,
    email_verified
)
VALUES (
    'lead.investigator@forensic.gov',
    'lead.investigator',
    'pbkdf2:sha256:600000$default_seed$e10adc3949ba59abbe56e057f20f883e',
    'Lead Forensic Officer',
    'CS-9912',
    'Crime Scene Investigation Unit',
    'Lead Investigator',
    1
)
ON CONFLICT (email) DO NOTHING;
