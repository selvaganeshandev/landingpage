-- Fix report_templates table to match the model
-- Add missing columns to report_templates

-- 1. Add template_type column
ALTER TABLE report_templates
ADD COLUMN IF NOT EXISTS template_type VARCHAR(20) NOT NULL DEFAULT 'predefined';

-- 2. Add grid_rows column
ALTER TABLE report_templates
ADD COLUMN IF NOT EXISTS grid_rows JSONB NOT NULL DEFAULT '[]'::jsonb;

-- 3. Add organisation_id column (nullable for predefined templates)
ALTER TABLE report_templates
ADD COLUMN IF NOT EXISTS organisation_id BIGINT NULL;

-- 4. Add created_by_id column (nullable)
ALTER TABLE report_templates
ADD COLUMN IF NOT EXISTS created_by_id BIGINT NULL;

-- 5. Add foreign key constraints
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'report_templates_organisation_id_fkey'
    ) THEN
        ALTER TABLE report_templates
        ADD CONSTRAINT report_templates_organisation_id_fkey
        FOREIGN KEY (organisation_id)
        REFERENCES organisations(id)
        ON DELETE CASCADE
        DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'report_templates_created_by_id_fkey'
    ) THEN
        ALTER TABLE report_templates
        ADD CONSTRAINT report_templates_created_by_id_fkey
        FOREIGN KEY (created_by_id)
        REFERENCES accounts(id)
        ON DELETE SET NULL
        DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;

-- 6. Drop and recreate the index with correct fields
DROP INDEX IF EXISTS report_tmpl_org_type_idx;
CREATE INDEX IF NOT EXISTS report_tmpl_org_type_idx
ON report_templates (organisation_id, template_type);

-- 7. Verify the changes
\d report_templates
