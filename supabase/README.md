# Supabase Integration for AI Crime Scene Detection

This directory contains configuration, PostgreSQL migrations, and seed scripts for connecting the AI Crime Scene Detection platform to **Supabase**.

## Directory Structure

```
supabase/
├── config.toml                              # Supabase project configuration
├── migrations/
│   └── 20261031000000_init_forensic_schema.sql  # Full forensic PostgreSQL schema with RLS
├── seed.sql                                 # Seed credentials for forensic officer
└── README.md                                # Setup instructions
```

## How to Connect to Supabase

1. **GitHub Integration**:
   - In your Supabase Dashboard, go to **Project Settings** > **Integrations** > **GitHub**.
   - Select repository: `rahul123-choudhary/AI-Crime-Scene-Detection`.
   - Set **Working directory** to `.` (the root of the repo, which contains the `supabase/` folder).
   - Click **Save / Connect**.
   - Supabase will automatically track and apply migrations from `supabase/migrations/`.

2. **Environment Configuration**:
   Add your Supabase Project API credentials to your `.env` file:

   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-supabase-anon-or-service-key
   ```

3. **Database Tables Included**:
   - `public.cases`: Case metadata, threat index, AI scene dynamics narrative, image/video paths.
   - `public.evidence_items`: Identified weapons, forensic traces, confidence %, bounding boxes, observed action states.
   - `public.audit_logs`: Complete forensic custody chain and action history.
   - `public.users`: Investigator profiles, badge credentials, and authentication records.
   - `public.analytics_events`: Telemetry and scene analysis performance events.

