# Integration and migration

## Do not copy the framework into product repositories

Install it as a versioned Python dependency or expose it behind a small internal HTTP service when the caller is not Python.

For Python products, pin a release or commit rather than tracking `main` implicitly.

## Existing project migration

Existing prompt and configuration systems do not need to be removed in one change.

### Step 1

Map the product's current profile and business configuration into `CommunicationRequest`.

Examples

Tutoring product

```python
request = tutoring_request(
    channel="profi",
    message_type="chat_reply",
    profile=current_profile.id,
    conversation=history,
    context={
        "client_name": order.client_name,
        "student_name": order.student_name,
        "profile_facts": current_profile.public_facts,
        "order": order.public_context,
    },
    business_rules=current_profile.communication_rules,
    voice=current_profile.voice,
)
```

Job-search product

```python
request = job_search_request(
    channel="hh",
    message_type="application",
    profile="backend",
    conversation=[],
    context={
        "vacancy": vacancy.summary,
        "candidate_facts": selected_resume.public_facts,
    },
)
```

### Step 2

Use `prepare()` with the existing LLM client.

This validates framework behavior without changing credentials, routing or model infrastructure.

### Step 3

Move generation into the framework with the preferred provider adapter.

### Step 4

After regression fixtures pass, delete duplicated local communication prompts, random style injection and overlapping validators from the product.

Browser automation, database state and delivery stay unchanged.

## Multiple profiles

Do not create separate framework forks for informatics, Chinese, Spanish, frontend or backend.

The product selects a profile and supplies its facts at runtime. Channel and message-type behavior stays shared.

## Non-Python products

Keep this repository as the source of truth and expose a small service wrapper around `prepare()` and `generate()` rather than reimplementing policies in Java, JavaScript or Go.

A future HTTP contract should mirror `CommunicationRequest` and `CommunicationResult` without exposing provider-specific details.
