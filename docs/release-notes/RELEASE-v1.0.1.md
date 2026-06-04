# PrivX Reporter v1.0.1

Security update.

## Changes

- Added script to upgrade Python libraries with vulnerabilities
  - Script is used during Docker image creation
  - You can now run `post_install --secure` after installation to upgrade the libraries for the CLI.