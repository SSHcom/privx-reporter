# Installation

PrivX Reporter supports two deployment models. Each guide is self-contained — pick the one that matches your environment and follow it end-to-end.

## [Standalone](STANDALONE.md)

All components (CLI, Sync Server, UI, and local PostgreSQL databases) run on a single host via Docker Compose. No external database provisioning is needed.

Best for evaluations, small deployments, or environments where a single host is sufficient.

## [Distributed](DISTRIBUTED.md)

The CLI is installed on one host; the Sync Server and UI run as separate Docker containers (on the same or different hosts); databases are provisioned externally.

Best for production environments where database management, networking, and scaling are handled outside of Reporter.
