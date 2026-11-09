# Zotero SQLite Queries

## Contents

- Safe database copy
- Find an item
- Read metadata and creators
- Resolve PDF attachments

## Safe database copy

Prefer the OpenAI Zotero capability or Zotero local API. Use SQLite only when the required local attachment path or metadata is unavailable there.

Create a consistent, read-only snapshot with the bundled cross-platform helper:

```text
python scripts/zotero_snapshot.py --json
```

The helper reads `ZOTERO_DATA_DIR`, copies the database and active WAL into a unique operating-system temporary directory, verifies that the source did not change during the copy, and runs `PRAGMA quick_check`. Pass `--zotero-dir <path>` when the environment variable is unavailable. Remove the returned workspace after the workflow.

## Find an item

Search recent candidate items through `itemData` and `itemDataValues`, then confirm the title or DOI before continuing. Always parameterize values when using a script; do not interpolate untrusted text into SQL.

## Read metadata and creators

Join `itemData`, `itemDataValues`, and `fields` for field values. Join `itemCreators` and `creators`, ordered by `orderIndex`, for the author list. Read the parent item key from `items.key`.

## Resolve PDF attachments

Query `itemAttachments` by `parentItemID` and `contentType = 'application/pdf'`. For a `storage:<filename>` path, resolve:

```text
$ZOTERO_DATA_DIR/storage/<attachment-key>/<filename>
```

Verify the resulting file type before opening it.
