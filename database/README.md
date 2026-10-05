# Database Directory — PG Management System

This directory contains the database definition and seed data scripts for MySQL 8.0 / InnoDB.

---

## 1. Directory Contents

- `schema.sql`: Full DDL script creating all 17 normalized tables from [`docs/DATABASE_SCHEMA.md`](../docs/DATABASE_SCHEMA.md). Includes foreign keys with cascading/restrict rules, unique constraints, and optimized indexes.
- `seed_demo.sql`: Complete, realistic demo dataset including administrative staff, branch managers, resident tenants, properties, rooms, beds across all statuses, active allocations, rent invoices, payments, security deposits in escrow, utility meters, complaints, and notices.

---

## 2. Standards & Constraints

1. **Storage Engine**: `InnoDB` across all 17 tables for transaction safety and ACID guarantees.
2. **Encoding**: `utf8mb4` charset with `utf8mb4_unicode_ci` collation for multi-language and symbol support.
3. **Monetary Precision**: All monetary values are defined as `DECIMAL(10,2)`.
4. **Concurrency Locking**: Atomic check-ins use `SELECT ... FOR UPDATE` row locks to prevent simultaneous double-allocations.
5. **Bed Lifecycle**: State machine transitions strictly follow:
   `AVAILABLE` → `OCCUPIED` → `UNDER_MAINTENANCE` → `AVAILABLE`.
6. **Data Retention**: Checked-out tenants retain their full profile and tenancy history in the database.

---

## 3. Database Initialization Commands

```bash
# Connect and create database
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS pg_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Apply schema
mysql -u root -p pg_management < database/schema.sql

# Load demo data
mysql -u root -p pg_management < database/seed_demo.sql
```
