-- Athena DDL for the curated transaction layer written by
-- etl/glue_job_transaction_etl.py. Run once (or let the Glue job's
-- enableUpdateCatalog handle it automatically on every run - this file is
-- here for the initial setup / disaster-recovery case).

CREATE DATABASE IF NOT EXISTS subsense;

CREATE EXTERNAL TABLE IF NOT EXISTS subsense.transactions_curated (
    txn_date              date,
    merchant_raw          string,
    merchant_normalized   string,
    amount                double,
    category              string
)
PARTITIONED BY (year int, month int)
STORED AS PARQUET
LOCATION 's3://subsense-curated/transactions/'
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');

-- After adding new partitions outside of Glue's auto-catalog-update (e.g. a
-- manual backfill), sync the partition metadata:
-- MSCK REPAIR TABLE subsense.transactions_curated;
