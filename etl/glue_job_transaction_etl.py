"""
AWS Glue job: raw transaction CSVs (S3 bronze) -> cleaned, categorized,
partitioned Parquet (S3 silver) + Glue Data Catalog update.

This is the batch-scale counterpart to backend/app/ingestion/csv_parser.py +
categorizer.py, which handle the same normalization for single-file uploads
through the API. The merchant-normalization and category rules are
intentionally duplicated here as a self-contained UDF rather than imported,
since Glue jobs run in a distributed Spark cluster with their own Python
environment - in a real deployment, `app/ingestion/categorizer.py` would be
packaged as a wheel and shipped via `--extra-py-files` so both paths share
one source of truth instead of two rule sets drifting apart. Documented here,
not hidden, because that's a real maintenance tradeoff a reviewer should see.

Run as a Glue job (Glue 4.0+, Python 3.10, G.1X workers):
    --JOB_NAME              subsense-transaction-etl
    --RAW_S3_PATH            s3://subsense-raw/transactions/
    --CURATED_S3_PATH        s3://subsense-curated/transactions/
    --GLUE_DATABASE          subsense
    --GLUE_TABLE             transactions_curated
"""
import re
import sys

from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

args = getResolvedOptions(
    sys.argv,
    ["JOB_NAME", "RAW_S3_PATH", "CURATED_S3_PATH", "GLUE_DATABASE", "GLUE_TABLE"],
)

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# --------------------------------------------------------------------------
# Merchant normalization + categorization (mirrors app/ingestion/categorizer.py)
# --------------------------------------------------------------------------
_NOISE_PREFIXES = [
    r"^SQ \*", r"^SP \*", r"^PAYPAL \*", r"^PP\*", r"^TST\*",
    r"^POS DEBIT ", r"^ACH DEBIT ", r"^DEBIT CARD PURCHASE ", r"^RECURRING PAYMENT ",
]
_NOISE_SUFFIXES = [
    r"\s+\d{3}-\d{3}-\d{4}$", r"\s+#\d+$", r"\s+\d{4,}$", r"\s+[A-Z]{2}$", r"\.COM$", r"\*\d+$",
]
_CATEGORY_RULES = {
    "Streaming": ["netflix", "hulu", "disney+", "disney plus", "max", "hbo", "peacock",
                  "paramount", "spotify", "apple music", "youtube premium", "audible", "crunchyroll"],
    "Software & AI": ["openai", "chatgpt", "anthropic", "claude", "adobe", "microsoft 365",
                       "notion", "figma", "github", "dropbox", "icloud", "google one",
                       "1password", "grammarly"],
    "Fitness & Health": ["planet fitness", "equinox", "peloton", "gym", "yoga", "classpass",
                          "whoop", "headspace", "calm"],
    "News & Reading": ["nyt", "new york times", "wsj", "wall street journal", "medium",
                        "kindle unlimited", "audible"],
    "Food Delivery": ["doordash", "grubhub", "uber eats", "instacart", "hellofresh", "blue apron"],
    "Utilities": ["comcast", "xfinity", "verizon", "at&t", "t-mobile", "spectrum",
                  "con edison", "pge", "national grid"],
    "Transport": ["uber", "lyft", "shell", "exxon", "chevron"],
    "Shopping": ["amazon", "walmart", "target", "costco"],
}


def normalize_merchant(raw_name: str) -> str:
    if not raw_name:
        return ""
    name = raw_name.strip().upper()
    for pattern in _NOISE_PREFIXES:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    for pattern in _NOISE_SUFFIXES:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    name = re.sub(r"[^\w\s&+]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title() if name else raw_name.strip().title()


def categorize(normalized_name: str) -> str:
    lowered = (normalized_name or "").lower()
    for category, keywords in _CATEGORY_RULES.items():
        for kw in keywords:
            if kw in lowered:
                return category
    return "Other"


normalize_udf = F.udf(normalize_merchant, StringType())
categorize_udf = F.udf(categorize, StringType())

# --------------------------------------------------------------------------
# Extract: raw CSVs from S3 (bronze)
# --------------------------------------------------------------------------
raw_df = (
    spark.read.option("header", True)
    .option("inferSchema", False)
    .csv(args["RAW_S3_PATH"])
)

# --------------------------------------------------------------------------
# Transform: clean amount, normalize merchant, categorize, derive partitions
# --------------------------------------------------------------------------
cleaned = (
    raw_df
    .withColumn("amount_clean", F.regexp_replace(F.col("amount"), r"[\$,]", "").cast(DoubleType()))
    .withColumn("txn_date", F.to_date(F.col("date")))
    .withColumn("merchant_normalized", normalize_udf(F.col("description")))
    .withColumn("category", categorize_udf(F.col("merchant_normalized")))
    .withColumn("year", F.year(F.col("txn_date")))
    .withColumn("month", F.month(F.col("txn_date")))
    .filter(F.col("txn_date").isNotNull() & F.col("amount_clean").isNotNull() & (F.col("amount_clean") != 0))
    .select(
        F.col("txn_date"),
        F.col("description").alias("merchant_raw"),
        F.col("merchant_normalized"),
        F.abs(F.col("amount_clean")).alias("amount"),
        F.col("category"),
        F.col("year"),
        F.col("month"),
    )
    .dropDuplicates(["txn_date", "merchant_normalized", "amount"])  # same dedup guarantee as the API path
)

# --------------------------------------------------------------------------
# Load: partitioned Parquet to S3 (silver) + Glue Catalog
# --------------------------------------------------------------------------
dynamic_frame = DynamicFrame.fromDF(cleaned, glueContext, "cleaned_transactions")

glueContext.write_dynamic_frame.from_options(
    frame=dynamic_frame,
    connection_type="s3",
    connection_options={
        "path": args["CURATED_S3_PATH"],
        "partitionKeys": ["year", "month"],
    },
    format="parquet",
    format_options={"compression": "snappy"},
    transformation_ctx="write_curated",
)

# Keep the Data Catalog in sync so Athena sees new partitions immediately
glueContext.getSink(
    connection_type="s3",
    path=args["CURATED_S3_PATH"],
    enableUpdateCatalog=True,
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=["year", "month"],
).setCatalogInfo(catalogDatabase=args["GLUE_DATABASE"], catalogTableName=args["GLUE_TABLE"])

job.commit()
