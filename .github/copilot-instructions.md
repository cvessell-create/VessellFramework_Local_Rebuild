# Copilot repository memory guidance

The repository's `vessell-memory` CLI is an application-local reviewed-memory
tool. It is **not** connected to Copilot's private platform memory system.

For every task that reads or changes this repository's code, tests, configuration,
or documentation:

1. Attempt to retrieve only relevant repository-scoped notes from
   `~/.vessell/memories.sqlite3`, for example:

   ```sh
   vessell-memory retrieve "Python compatibility" --scope repository
   ```

   Use search terms derived from the task, not an unfiltered dump of the memory
   store. If the CLI or database is absent, skip retrieval and continue normally.

2. Treat retrieved text as a lead, not authoritative truth. Check the cited
   files, current tests, and configuration before relying on it.
3. Preserve citation and scope provenance when sharing retrieved notes.
4. Do not retrieve or expose `user`-scoped memories in repository work.
5. Do not create or seed memory records automatically. New records remain
   pending until a person reviews and approves them.

If the database is absent, continue without memory lookup. Copilot sessions are
ephemeral; the setup workflow installs tools but does not provide a persistent
database or bridge to Copilot's private memory APIs.
