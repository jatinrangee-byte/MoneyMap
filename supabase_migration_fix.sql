-- ============================================================
-- MoneyMap — Supabase Migration: Add missing columns
-- Run this in: https://supabase.com/dashboard/project/arhfznmlbjxevsqstkcp/sql/new
-- ============================================================

-- Add 'is_anomaly' column if it doesn't exist
ALTER TABLE public.transactions
  ADD COLUMN IF NOT EXISTS is_anomaly SMALLINT NOT NULL DEFAULT 0;

-- Add 'note' column if it doesn't exist
ALTER TABLE public.transactions
  ADD COLUMN IF NOT EXISTS note TEXT;

-- Verify: list all columns in transactions table
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'transactions'
ORDER BY ordinal_position;
