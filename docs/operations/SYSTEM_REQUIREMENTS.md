# System Requirements

This document outlines the minimum hardware requirements for running PrivX Reporter based on environment throughput.

## Components

Reporter consists of 4 components that can run on a single server or be distributed:

| Component          | Description                                                                                  |
| ------------------ | -------------------------------------------------------------------------------------------- |
| **Data Database**  | TimescaleDB (PostgreSQL) — stores synced audit events, connections, trends, concurrent stats |
| **Admin Database** | PostgreSQL — stores user accounts, report config, session data                               |
| **Sync Server**    | Python process — syncs data from PrivX API to the data database                              |
| **UI / CLI**       | Streamlit web app + CLI report tool                                                          |

## Sizing Profiles

Sizing is primarily driven by the **data database** (TimescaleDB), which stores synced historical data from PrivX. The admin database and generated report files are negligible in comparison.

Sizing depends on:
- Number of PrivX connections per day
- Number of audit events per day
- Data retention period (configurable, default 15 days)
- Number of concurrent UI users

### Low Throughput

Typical: small-to-mid org, 1,000–5,000 connections/day, <50,000 audit events/day, 15-day retention.

| Resource   | Minimum                                                            |
| ---------- | ------------------------------------------------------------------ |
| **CPU**    | 2 vCPU                                                             |
| **Memory** | 4 GB RAM                                                           |
| **Disk**   | 20 GB SSD                                                          |
| **OS**     | RHEL 9 (tested). See Software Requirements for other supported OS. |

Estimated data DB size: ~2–4 GB at 15-day retention.

### Medium Throughput

Typical: mid-to-large org, 5,000–20,000 connections/day, 50,000–200,000 audit events/day, 30-day retention.

| Resource   | Minimum                                                            |
| ---------- | ------------------------------------------------------------------ |
| **CPU**    | 4 vCPU                                                             |
| **Memory** | 8 GB RAM                                                           |
| **Disk**   | 50 GB SSD                                                          |
| **OS**     | RHEL 9 (tested). See Software Requirements for other supported OS. |

Estimated data DB size: ~10–35 GB at 30-day retention.

### High Throughput

Typical: enterprise, 20,000–50,000+ connections/day, >200,000 audit events/day, 90-day retention, multiple concurrent UI users.

| Resource   | Minimum                                                            |
| ---------- | ------------------------------------------------------------------ |
| **CPU**    | 8 vCPU                                                             |
| **Memory** | 16 GB RAM                                                          |
| **Disk**   | 200 GB SSD                                                         |
| **OS**     | RHEL 9 (tested). See Software Requirements for other supported OS. |

Estimated data DB size: ~50–150 GB at 90-day retention.

---

## Storage Breakdown

Based on observed production data (6.4M connection rows = 34 GB including indexes):

| Table              | Avg Row Size (with indexes) | Growth Rate                        | Notes                                                              |
| ------------------ | --------------------------- | ---------------------------------- | ------------------------------------------------------------------ |
| `connection`       | ~5.5 KB                     | Proportional to PrivX connections  | Largest table. Index overhead is significant (~98% of total size). |
| `audit_event`      | ~1.7 KB                     | Proportional to PrivX audit volume | Much smaller than connections.                                     |
| `concurrent_stats` | ~0.5 KB                     | 1 row/minute = ~43K rows/month     | Minimal footprint (~20 MB/month)                                   |
| `system_trend`     | ~0.5 KB                     | 1 row/day = ~90 rows max           | Negligible                                                         |

**Key observation:** The `connection` table's GIN index on the JSONB `data` column dominates storage. In a real deployment with 6.4M rows, data was 767 MB but total size (with indexes) was 34 GB.

---

## Software Requirements

| Software              | Version                           |
| --------------------- | --------------------------------- |
| Python                | 3.13+                             |
| PostgreSQL (admin DB) | 16+                               |
| TimescaleDB (data DB) | Latest (PostgreSQL 16–18)         |
| OS                    | Linux x86_64 or ARM64 (see below) |

### Operating System

Reporter is tested and supported on **RHEL 9** (and compatible derivatives like Rocky Linux 9, AlmaLinux 9).

It may work on other Linux distributions with minor adjustments:
- RHEL 8
- Ubuntu 22.04+
- Amazon Linux 2023


### Python Dependencies

Managed via `uv` (recommended) or `pip`. Key dependencies:
- SQLAlchemy 2.0+
- Streamlit 1.56+
- psycopg2-binary
- bcrypt 5.0+
- pandas

---

## Network Requirements

| Source      | Destination  | Port | Protocol   | Purpose                          |
| ----------- | ------------ | ---- | ---------- | -------------------------------- |
| Sync Server | PrivX Server | 443  | HTTPS      | API data sync                    |
| Sync Server | Data DB      | 5432 | PostgreSQL | Write synced data                |
| Sync Server | Admin DB     | 5432 | PostgreSQL | Read event config                |
| UI          | Data DB      | 5432 | PostgreSQL | Dashboard queries                |
| UI          | Admin DB     | 5432 | PostgreSQL | User auth, config                |
| UI          | PrivX Server | 443  | HTTPS      | Live API calls (reports, counts) |
| Browser     | UI           | 8501 | HTTPS      | Streamlit web interface          |

---

## Scaling Notes

- **Disk I/O** is the primary bottleneck for large deployments. Use SSD storage.
- **Memory** is important for PostgreSQL shared buffers and TimescaleDB chunk caching. Allocate 25% of RAM to `shared_buffers`.
- **CPU** matters during sync bursts (adaptive windowing) and concurrent report generation.
- **Retention period** is the biggest lever for disk usage. Reducing from 90 to 30 days cuts storage by ~65%.
- The sync server's adaptive windowing prevents API overload but increases CPU usage during catch-up periods.
- For high-throughput environments, consider separating the data database onto its own server.
