# MP2027 instructions for AI agents

## Release and update work

Before changing a version, building a Setup, creating a `.mpupdate`, copying files to a share, or publishing `latest.json`, read [`docs/handover/release_update_playbook.md`](docs/handover/release_update_playbook.md) in full.

This repository uses the `HASH_ONLY_LAN` update flow. Do not create, request, search for, restore, or require signing keys. Do not add `manifest.sig`, `key_id`, `trusted_signing_keys`, private-key files, or a key-provisioning step unless the project owner explicitly changes this policy.

The company-controlled UNC update folder is the trust boundary. Keep SHA-256 catalog and manifest checks, safe extraction, compatibility checks, health checks, backups, and rollback behavior intact.
