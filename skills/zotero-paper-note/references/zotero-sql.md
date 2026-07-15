# Zotero SQLite Queries

## Contents

- Safe database copy
- Find an item
- Read metadata and creators
- Resolve PDF attachments

## Safe database copy

Never query the live database while Zotero may be writing to it:

```bash
cp "$ZOTERO_DATA_DIR/zotero.sqlite" "$TMPDIR/zotero-query.sqlite"
```

Use a unique temporary filename for concurrent runs and remove it after the workflow.

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
