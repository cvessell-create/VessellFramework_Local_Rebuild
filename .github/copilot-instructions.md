# Copilot repository memory guidance

The repository's `vessell-memory` CLI is an application-local reviewed-memory
tool. It is **not** connected to Copilot's private platform memory system.

For a repository task where prior project decisions or conventions are useful:

1. If `~/.vessell/memories.sqlite3` already exists, retrieve only relevant
   repository-scoped notes, for example:

   ```sh
   vessell-memory retrieve "Python compatibility" --scope repository
   ```

2. Treat retrieved text as a lead, not authoritative truth. Check the cited
   files, current tests, and configuration before relying on it.
3. Preserve citation and scope provenance when sharing retrieved notes.
4. Do not retrieve or expose `user`-scoped memories in repository work.
5. Do not create or seed memory records automatically. New records remain
   pending until a person reviews and approves them.

If the database is absent, continue without memory lookup. Copilot sessions are
ephemeral; the setup workflow installs tools but does not provide a persistent
database or bridge to Copilot's private memory APIs.
