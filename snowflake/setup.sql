-- Monday Morning Brief: Snowflake setup
-- Run in Snowsight as ACCOUNTADMIN. Safe to rerun.

USE ROLE ACCOUNTADMIN;

-- Small warehouse that shuts off after 60 seconds idle
CREATE WAREHOUSE IF NOT EXISTS MMB_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

-- Project database and landing schema for the raw CSV files
CREATE DATABASE IF NOT EXISTS MMB;
CREATE SCHEMA IF NOT EXISTS MMB.RAW;

-- Project role: can reach only this warehouse and database
CREATE ROLE IF NOT EXISTS MMB_ROLE;
GRANT USAGE ON WAREHOUSE MMB_WH TO ROLE MMB_ROLE;
GRANT ALL ON DATABASE MMB TO ROLE MMB_ROLE;
GRANT ALL ON SCHEMA MMB.RAW TO ROLE MMB_ROLE;
GRANT ROLE MMB_ROLE TO ROLE SYSADMIN;

-- Service login for scripts and dbt: key-pair only, no password
-- Generate a key pair locally, then paste the public key below.
-- Never commit the private key.
CREATE USER IF NOT EXISTS MMB_SVC
  TYPE = SERVICE
  DEFAULT_ROLE = MMB_ROLE
  DEFAULT_WAREHOUSE = MMB_WH
  DEFAULT_NAMESPACE = MMB.RAW
  RSA_PUBLIC_KEY = '<PASTE_PUBLIC_KEY_HERE>';

GRANT ROLE MMB_ROLE TO USER MMB_SVC;
