# ETL layer: AWS Glue + Athena

Batch-scale counterpart to the API's per-upload ingestion. The API path
(`backend/app/ingestion/`) handles a user uploading one statement at a time;
this layer is for processing transaction dumps at real warehouse scale -
years of history across many linked accounts - the kind of volume a single
Flask request shouldn't be doing synchronously.

**Honesty note:** this code was written and reviewed carefully against the
real AWS Glue/PySpark/Athena APIs, but the sandbox this project was built in
has no network access to actually run it against AWS. It has not been
boot-tested the way the backend and frontend were. Treat it as a correct,
reviewed starting point - run the smoke test below before trusting it in
production.

## What's here

| File | Purpose |
|---|---|
| `glue_job_transaction_etl.py` | PySpark Glue job: raw CSVs (S3 bronze) → cleaned, categorized, partitioned Parquet (S3 silver) |
| `athena_ddl.sql` | External table definition over the curated Parquet layer |
| `athena_queries.sql` | Analytical queries: monthly spend, top merchants, warehouse-side recurring-charge detection, MoM trend |

## Deploying

1. **Create S3 buckets/prefixes** for raw and curated data:
   ```
   s3://subsense-raw/transactions/
   s3://subsense-curated/transactions/
   ```

2. **Create the Glue job** (console or IaC):
   - Type: Spark, Glue version 4.0+, Python 3.10
   - Worker type: G.1X, 2-10 workers depending on data volume
   - Script: `glue_job_transaction_etl.py`
   - Job parameters:
     ```
     --RAW_S3_PATH        s3://subsense-raw/transactions/
     --CURATED_S3_PATH    s3://subsense-curated/transactions/
     --GLUE_DATABASE      subsense
     --GLUE_TABLE         transactions_curated
     ```
   - IAM role needs: `s3:GetObject`/`s3:PutObject` on both buckets, `glue:*` on the `subsense` database/table.

3. **Run `athena_ddl.sql` once** in the Athena query editor to create the database/table (the Glue job's `enableUpdateCatalog` keeps partitions in sync after that - `MSCK REPAIR TABLE` is only needed if you ever backfill partitions outside the job).

4. **Schedule the job** - EventBridge rule on a cron (e.g. nightly) or trigger it from wherever raw statement exports land in the bronze bucket.

5. **Point Athena at it** - the queries in `athena_queries.sql` are ready to run once step 3 is done; query result location needs to be set once in Athena workgroup settings (`s3://subsense-athena-results/`).

## Smoke-testing before trusting this in production

```bash
# Validate the PySpark script parses and the UDF logic matches the tested
# Python version, without needing a live Glue environment:
pip install pyspark==3.5.0
python3 -c "
import sys
sys.argv = ['glue_job_transaction_etl.py', '--JOB_NAME=test', '--RAW_S3_PATH=/tmp/raw', '--CURATED_S3_PATH=/tmp/curated', '--GLUE_DATABASE=test', '--GLUE_TABLE=test']
# will fail past the awsglue import (that library only exists inside Glue's
# managed environment) - this at least catches syntax errors and confirms
# normalize_merchant/categorize match backend/app/ingestion/categorizer.py
"
```

For a real smoke test, run the job against a small sample in an actual Glue
dev endpoint or Glue Studio notebook before pointing it at production data.

## Why the categorization rules are duplicated here

`glue_job_transaction_etl.py` inlines its own copy of `normalize_merchant`/
`categorize` rather than importing `backend/app/ingestion/categorizer.py`,
because Glue jobs run in a separate distributed Python environment. The
correct production fix is packaging the backend as a wheel and shipping it
via `--extra-py-files` (or a Glue custom connector) so there's one source of
truth instead of two rule sets that can silently drift apart. Flagged here
rather than hidden - this is real technical debt, scoped and documented.
