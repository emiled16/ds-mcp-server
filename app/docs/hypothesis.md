# Hypotheses Log

## Overview
This document tracks the hypotheses considered during the implementation of the MCP Data Science Agent.

---

## Phase 0: Setup & Foundation

### H1: Redis as unified cache/broker ✅ VALIDATED
- **Hypothesis**: Using Redis for both Celery broker and tool caching simplifies infrastructure
- **Evidence**: Single Redis service handles both use cases efficiently
- **Outcome**: Reduced Docker services, simplified configuration

### H2: pytest-asyncio for async testing ✅ VALIDATED
- **Hypothesis**: pytest-asyncio with `asyncio_mode = auto` handles async test functions
- **Evidence**: All async tests run correctly without manual event loop management
- **Outcome**: Clean async test patterns established

---

## Phase 1: Core Infrastructure

### H3: Entity resolution in middleware ✅ VALIDATED
- **Hypothesis**: Middleware can automatically resolve entity_id references before tool execution
- **Evidence**: `resolve_entity_references` function extracts type hints and resolves entities
- **Outcome**: Tools receive full data payloads transparently

### H4: Hash-based caching for deterministic calls ✅ VALIDATED
- **Hypothesis**: MD5 hash of function name + args + kwargs provides unique cache keys
- **Evidence**: ToolCache correctly identifies repeated calls
- **Outcome**: Efficient caching with minimal collision risk

### H5: Celery for async job management ✅ VALIDATED
- **Hypothesis**: Celery with Redis backend handles long-running ML jobs well
- **Evidence**: Jobs can be submitted, tracked, and cancelled asynchronously
- **Outcome**: Non-blocking training workflows achieved

---

## Phase 2: Data Access & Exploration

### H6: Polars for fast data loading ✅ VALIDATED
- **Hypothesis**: Polars provides faster CSV/Excel loading than Pandas
- **Evidence**: Load operations complete quickly with efficient memory usage
- **Outcome**: Consistent data handling across tools

### H7: Statistical summaries reduce context ✅ VALIDATED
- **Hypothesis**: Returning statistics instead of raw data fits context window constraints
- **Evidence**: Agents receive useful summaries while full data is stored
- **Outcome**: Core ToolResponse pattern works as designed

### H8: Missing value analysis informs preprocessing ✅ VALIDATED
- **Hypothesis**: Automated missing value detection provides actionable recommendations
- **Evidence**: Tool suggests strategies (mean, median, mode, drop) based on patterns
- **Outcome**: Agents can make informed preprocessing decisions

---

## Phase 3: Feature Engineering

### H9: Dynamic transformation loading ✅ VALIDATED
- **Hypothesis**: Transformations can be loaded dynamically from the feature store library
- **Evidence**: `apply_transformation` discovers and instantiates transformation classes
- **Outcome**: 25+ transformations available without hardcoding

### H10: Pydantic configs for transformation parameters ✅ VALIDATED
- **Hypothesis**: Each transformation's config class defines valid parameters
- **Evidence**: Parameter validation catches errors before execution
- **Outcome**: Robust transformation pipeline

---

## Phase 4: Async Jobs

### H11: Job model tracks full lifecycle ✅ VALIDATED
- **Hypothesis**: Job entity captures submission, progress, completion, and errors
- **Evidence**: JobRepository supports all CRUD operations and status transitions
- **Outcome**: Complete job visibility for agents

### H12: Celery task revocation works for cancellation ✅ VALIDATED
- **Hypothesis**: Calling `revoke(terminate=True)` cancels running tasks
- **Evidence**: `cancel_job` tool successfully terminates jobs
- **Outcome**: Users can stop unwanted long-running jobs

---

## Phase 5: Note-Taking

### H13: Notes enable persistent agent memory ✅ VALIDATED
- **Hypothesis**: Notes with tags and references help agents track analysis
- **Evidence**: Full CRUD operations with search by title/content/tags
- **Outcome**: Agents can maintain context across sessions

### H14: Text search is sufficient for note retrieval ✅ VALIDATED
- **Hypothesis**: Case-insensitive keyword search covers most use cases
- **Evidence**: `search_notes` finds notes by partial matches
- **Outcome**: Simple but effective retrieval without complex indexing

---

## Phase 6: Testing

### H15: Unit tests validate core models ✅ VALIDATED
- **Hypothesis**: Testing Pydantic models ensures data integrity
- **Evidence**: 30 tests covering ToolResponse, Job, Note, middleware, cache
- **Outcome**: Confidence in model behavior

### H16: Mocking storage enables isolated tests ✅ VALIDATED
- **Hypothesis**: AsyncMock for storage backends enables fast unit tests
- **Evidence**: Tests run in 0.08s without actual DB/cache connections
- **Outcome**: Fast, reliable CI pipeline

---

## Phase 7: Observability

### H17: Structured logging aids debugging ✅ VALIDATED
- **Hypothesis**: Loguru + structlog provide better observability than print
- **Evidence**: Correlation IDs and structured output implemented
- **Outcome**: Traceable request flows

---

## Hypotheses Rejected or Modified

### H18: Type hints alone sufficient for entity resolution ⚠️ PARTIALLY VALIDATED
- **Original**: Type hints indicate which params are entity references
- **Issue**: Some tools have generic `str` types that aren't entities
- **Modified**: Entity resolution uses naming convention (`entity_id`, `dataset_id`) alongside types
- **Outcome**: Hybrid approach works better

### H19: All tools should be cached ⚠️ MODIFIED
- **Original**: Cache all tool results by default
- **Issue**: Some tools have side effects (create_note, submit_job)
- **Modified**: `cacheable` parameter in decorator controls caching
- **Outcome**: Selective caching prevents stale data issues

---

## Future Hypotheses to Explore

### H20: Vector embeddings for semantic note search 🔮 FUTURE
- **Hypothesis**: Embedding-based search would improve note retrieval
- **Status**: Not implemented, text search sufficient for MVP

### H21: OpenTelemetry for distributed tracing 🔮 FUTURE
- **Hypothesis**: Tracing across Celery/MongoDB/MinIO aids performance analysis
- **Status**: Not implemented, basic logging sufficient for MVP

### H22: JWT authentication for multi-tenant access 🔮 FUTURE
- **Hypothesis**: Token-based auth enables secure multi-user deployments
- **Status**: Not implemented, single-tenant focus for MVP

---

## Summary

| Status | Count |
|--------|-------|
| ✅ Validated | 17 |
| ⚠️ Modified | 2 |
| 🔮 Future | 3 |
| ❌ Rejected | 0 |

All core hypotheses were validated during implementation. The ToolResponse pattern successfully addresses context window limitations, and the layered architecture provides a solid foundation for future enhancements.
