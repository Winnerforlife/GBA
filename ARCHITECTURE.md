# Architecture and design decisions

## 1. Why Django REST Framework and this structure

DRF gives validation, serialization, routing, pagination and a browsable error model out of
the box, and Django gives the ORM, migrations and an admin to inspect data. For a small API
with a clear domain this keeps the code short and conventional, so any Django team can
maintain it. OpenAPI/Swagger comes from drf-spectacular.

The code is split into layers with one responsibility each:

- **models** – data and database-level guarantees (unique key, CHECK constraints, FK).
- **serializers** – input validation and the shape of responses, including a separate
  export contract.
- **services** – business rules (status transitions, "results only for open samples",
  approval). They are plain functions, easy to test and reuse outside HTTP.
- **views** – thin: parse the request, call a service, return a response.

ViewSets expose only the operations the specification asks for (mixins instead of
`ModelViewSet`), so there is no accidental PUT or DELETE.

## 2. Data model

- `Sample`: internal `id`, unique `sample_id` (business key), `order_id`, `client_id`, `status`.
- `Result`: internal `id` (exposed as `result_id`), foreign key to `Sample`, `parameter`,
  `value`, `unit`, `status`.

Decisions:

- The API addresses samples by `sample_id`, while the foreign key uses the internal `id`.
  The business key can change in future without cascading updates.
- `order_id` and `client_id` are plain fields: the task does not need Order or Client
  entities. They are indexed for filtering.
- `on_delete=PROTECT`: a sample with results cannot be deleted, so lab data is never lost
  silently.
- `value` is a `FloatField` so JSON numbers stay numbers (`12.5`). `DecimalField` would be more
  exact but DRF serializes it as a string by default. NaN and infinity are rejected.
- There is no unique constraint on `(sample, parameter)`: in a real lab a parameter is often
  re-measured, so this should be a business decision, not an accident of the schema.
- An index on `(sample, status)` serves the export query.

## 3. Statuses of samples and results

Both are `TextChoices` enums, enforced at three levels: serializer choices, model `choices`,
and a database `CHECK` constraint.

Sample status is a small state machine kept in one dictionary in `services.py`:

```
registered ──► in_progress ──► completed (final)
    │               │
    └──► cancelled ◄┘          (final)
```

Result status is `draft → approved`. Approval is one-way and has its own endpoint; clients
cannot create or edit a result as approved.

Consistency rules, all in the service layer:

- results can be added or approved only while the sample is `registered` or `in_progress`;
- the sample row is locked (`select_for_update`) inside a transaction while a result is
  created or approved, so a concurrent status change cannot slip in (effective on PostgreSQL);
- export includes only approved results, with the filter in a single `Prefetch`.

Error semantics: 400 for invalid input, 404 for unknown objects, 409 when the input is valid
but conflicts with the current state.

## 4. Extending towards ERP / CRM / customer portal / e-commerce

The export is a separate, versionable contract (`SampleExportSerializer`) that does not
expose internal ids. Next steps, in order of value:

1. **Authentication and authorization**: API keys or OAuth2 client credentials per
   integrating system; restrict the export by `client_id` for a customer portal.
2. **Push instead of pull**: emit an event when a result is approved or a sample completes
   (outbox table plus a Celery worker) and deliver it by webhook, with retries and delivery
   status. This avoids polling `/integration/export`.
3. **Idempotency and delivery tracking**: store what was sent to which system and when;
   support `updated_since` for incremental sync.
4. **Versioned API** (`/v1/`) so the export contract can evolve without breaking consumers.
5. **Per-system mapping layer**: adapters that translate the neutral export to ERP, CRM or
   e-commerce formats, instead of adding system-specific fields to the core model.
6. **Bulk export** by order or client, with pagination.
