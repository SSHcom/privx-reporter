ENV_SOURCE_OPTIONS = [
    ("db", "database (recommended — remaining config is done as super admin after setup)"),
    ("env", ".env file (configure all remaining values here now)"),
]

ENV_SOURCE_DEFAULT = "db"

DB_TOPOLOGY_OPTIONS = [
    ("same_instance", "same instance (copy data DB values to admin DB)"),
    ("separate_instances", "separate instances (prompt admin DB values separately)"),
]

DB_TOPOLOGY_DEFAULT = "same_instance"

CA_CERT_MODE_OPTIONS = [
    ("skip", "skip for now (leave PRIVX_CA_CERT empty)"),
    ("set", "set PRIVX_CA_CERT now"),
]

CA_CERT_MODE_DEFAULT = "skip"

SYNC_SERVER_HOST_OPTIONS = [
    ("no", "no (default, sync server is running elsewhere)"),
    ("yes", "yes (this host will run the sync server)"),
]

SYNC_SERVER_HOST_DEFAULT = "no"

UI_SERVER_HOST_OPTIONS = [
    ("no", "no (default, UI server is running elsewhere)"),
    ("yes", "yes (this host will run the UI server)"),
]

UI_SERVER_HOST_DEFAULT = "no"
