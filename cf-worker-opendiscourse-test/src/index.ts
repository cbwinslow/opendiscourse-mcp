      // =====================================================================
      // Cloudflare Worker: opendiscourse-ingest-worker
      // Summary:
      //   - Receives HTTP requests to ingest gov-data documents.
      //   - Validates input (source_system, source_type, payload[]).
      //   - Calls external AI/agent endpoint for enrichment if configured.
      //   - Uses Hyperdrive-bound PostgreSQL connection for upserts.
      //   - Writes ingestion_jobs, ingestion_documents, ingestion_events.
      //   - Uses ON CONFLICT to avoid duplicates by doc_id & hash.
      // =====================================================================

      import { Env } from './types';

      export default {
        async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
          const url = new URL(request.url);

          if (request.method === 'GET' && url.pathname === '/health') {
            return new Response(JSON.stringify({ status: 'ok', worker: 'opendiscourse-ingest' }), {
              headers: { 'Content-Type': 'application/json' },
            });
          }

          if (request.method !== 'POST') {
            return new Response(JSON.stringify({ error: 'Method not allowed' }), { status: 405 });
          }

          let body: any;
          try {
            body = await request.json();
          } catch (err) {
            return new Response(JSON.stringify({ error: 'Invalid JSON body' }), { status: 400 });
          }

          const { source_system, source_type, documents } = body || {};

          if (!source_system || !source_type || !Array.isArray(documents) || documents.length === 0) {
            return new Response(JSON.stringify({
              error: 'Missing required fields',
              required: ['source_system', 'source_type', 'documents[]'],
            }), { status: 400 });
          }

          const client = env.OPENDISCOURSE_DB; // Hyperdrive binding

          // 1) Create ingestion job row
          const jobIdRow = await client.query(
            `INSERT INTO ingestion.ingestion_jobs
             (source_system, source_type, status, metadata)
             VALUES ($1, $2, 'running', $3::jsonb)
             RETURNING job_id`,
            [source_system, source_type, JSON.stringify({ worker: 'cloudflare', received_docs: documents.length })]
          );

          const jobId = jobIdRow.rows[0].job_id;

          let total = 0;
          let newRecords = 0;
          let updatedRecords = 0;
          let duplicateRecords = 0;
          let errorCount = 0;

          for (const doc of documents) {
            total += 1;
            try {
              const docId = doc.id || doc.doc_id;
              if (!docId) {
                errorCount += 1;
                await logEvent(client, jobId, 'warning', 'Document missing id/doc_id', { docSample: doc });
                continue;
              }

              const payloadJson = JSON.stringify(doc);

              // Optional AI enrichment
              let enrichedPayload = doc;
              if (env.INGEST_AI_ENDPOINT_URL) {
                try {
                  const aiResp = await fetch(env.INGEST_AI_ENDPOINT_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ source_system, source_type, document: doc }),
                  });
                  if (aiResp.ok) {
                    const aiJson = await aiResp.json();
                    enrichedPayload = aiJson.enriched_document || doc;
                  } else {
                    await logEvent(client, jobId, 'warning', 'AI enrichment failed', {
                      status: aiResp.status,
                      statusText: aiResp.statusText,
                    });
                  }
                } catch (e) {
                  await logEvent(client, jobId, 'warning', 'AI enrichment error', { error: String(e) });
                }
              }

              const finalPayloadJson = JSON.stringify(enrichedPayload);

              const hashRow = await client.query(
                `SELECT encode(digest($1, 'sha256'), 'hex') AS hash`,
                [finalPayloadJson]
              );
              const hash = hashRow.rows[0].hash;

              const upsertResult = await client.query(
                `INSERT INTO ingestion.ingestion_documents AS d
                 (doc_id, job_id, source_system, source_type, retrieved_at,
                  last_updated_at, payload, hash_sha256, is_duplicate, metadata)
                 VALUES ($1, $2, $3, $4, now(), now(), $5::jsonb, $6, false, $7::jsonb)
                 ON CONFLICT (doc_id)
                 DO UPDATE SET
                   job_id = EXCLUDED.job_id,
                   source_system = EXCLUDED.source_system,
                   source_type = EXCLUDED.source_type,
                   last_updated_at = now(),
                   payload = EXCLUDED.payload,
                   hash_sha256 = EXCLUDED.hash_sha256,
                   is_duplicate = (d.hash_sha256 = EXCLUDED.hash_sha256),
                   metadata = EXCLUDED.metadata
                 RETURNING (xmax = 0) AS inserted, is_duplicate`,
                [
                  docId,
                  jobId,
                  source_system,
                  source_type,
                  finalPayloadJson,
                  hash,
                  JSON.stringify({ worker: 'opendiscourse-ingest-worker' }),
                ]
              );

              const row = upsertResult.rows[0];
              if (row.inserted) {
                newRecords += 1;
              } else if (row.is_duplicate) {
                duplicateRecords += 1;
              } else {
                updatedRecords += 1;
              }

            } catch (err) {
              errorCount += 1;
              await logEvent(client, jobId, 'error', 'Failed to upsert document', { error: String(err) });
            }
          }

          // 3) Update job stats
          await client.query(
            `UPDATE ingestion.ingestion_jobs
             SET status = $2,
                 finished_at = now(),
                 total_records = $3,
                 new_records = $4,
                 updated_records = $5,
                 duplicate_records = $6,
                 error_count = $7
             WHERE job_id = $1`,
            [jobId, errorCount > 0 ? 'failed' : 'succeeded', total, newRecords, updatedRecords, duplicateRecords, errorCount]
          );

          return new Response(
            JSON.stringify({
              job_id: jobId,
              total_records: total,
              new_records: newRecords,
              updated_records: updatedRecords,
              duplicate_records: duplicateRecords,
              error_count: errorCount,
            }),
            { headers: { 'Content-Type': 'application/json' } }
          );
        },
      } satisfies ExportedHandler<Env>;

      async function logEvent(client: any, jobId: string, level: string, message: string, context: any) {
        try {
          await client.query(
            `INSERT INTO ingestion.ingestion_events
             (job_id, level, message, context)
             VALUES ($1, $2, $3, $4::jsonb)`,
            [jobId, level, message, JSON.stringify(context || {})]
          );
        } catch (err) {
          // Last-ditch logging; cannot throw or we risk losing context entirely.
          console.error('Failed to log event', err);
        }
      }