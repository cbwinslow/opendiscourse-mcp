-- GovInfo (GPO) schema for bulk data repository ingestion
-- Many collections are XML heavy; store parsed records with normalized fields plus raw JSON

CREATE TABLE IF NOT EXISTS govinfo_documents (
  id TEXT PRIMARY KEY,
  collection TEXT,
  date DATE,
  title TEXT,
  url TEXT,
  metadata JSONB,
  raw JSONB,
  created_on TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_govinfo_documents_collection ON govinfo_documents(collection);
CREATE INDEX IF NOT EXISTS idx_govinfo_documents_date ON govinfo_documents(date);
