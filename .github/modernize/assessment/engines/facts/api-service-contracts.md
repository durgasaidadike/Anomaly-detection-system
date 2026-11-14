# API & Service Communication Contracts

The repository currently exposes one implemented Spring Boot REST endpoint and one configured outbound Flask integration. Dashboard endpoints are proposed contract targets only; they are not implemented in the current source tree.

## Service Catalog

| Service | Port | Category | Purpose |
|---|---:|---|---|
| `prism-backend` | 8080 | API Layer | Spring Boot API boundary, response envelopes, health endpoint, and the integration boundary for intelligence services. |
| `flask-gateway` | 5000 (configured) | Business | Configured downstream intelligence service for event analysis. The Flask implementation exists at the repository root in `app.py`, outside the Spring Boot backend module, and exposes `/analyze-event`. |
| PRISM React frontend | Vite development port (not configured in backend) | Observability | Dashboard presentation and client-side health polling through relative Spring Boot `/api` paths. |

## API Endpoints Inventory

| Service | Method | Path | Request Type | Response Type |
|---|---|---|---|---|
| `prism-backend` / `HealthController` | GET | `/api/health` | None | `ApiResponseEnvelope<Map<String, String>>`; HTTP 200 |
| `flask-gateway` / configured client | POST | `/analyze-event` | `request.payload()` serialized as JSON from `ApiRequestEnvelope<Map<String, Object>>`; request ID, correlation ID, and timestamp are headers | Successful JSON object parsed as `JsonNode`; non-2xx responses become downstream failures |

### Proposed, not implemented dashboard endpoints

The following read-only paths are dashboard contract candidates and are intentionally not listed as implemented endpoints:

`GET /api/v1/dashboard/overview`, `/events`, `/patterns`, `/risks`, `/recoveries`, `/analytics`, and `/health`.

## Management & Observability Endpoints

| Service | Endpoint | Custom Metrics |
|---|---|---|
| `prism-backend` | `/actuator/health` | None identified; framework management health endpoint |
| `prism-backend` | `/actuator/info` | None identified; framework management information endpoint |
| `prism-backend` | `/api/health` | None identified; application health envelope for the dashboard client |

Spring Boot Actuator exposure is configured for `health,info`. No custom Micrometer metric registrations were found.
The proposed `/api/v1/dashboard/health` is a distinct future aggregate dashboard operation and is not implemented.

## DTOs & Contracts

The Spring Boot API uses immutable Java records:

- `ApiResponseEnvelope<T>` is the gateway-level response envelope. It carries `status`, `timestamp`, `requestId`, `processingTime`, `data`, and an immutable error list.
- `ApiRequestEnvelope<T>` is the integration request envelope. It carries request, timestamp, session, user, project, and payload context.
- `ApiError` is the standardized error item type.
- `Map<String, String>` is currently the health endpoint's service-level data payload.
- `JsonNode` is the current downstream Flask response boundary; no typed intelligence response DTO exists yet.
- `AuthenticationRequest`, `AuthenticationContext`, `AuthorizationRequest`, and `AuthorizationContext` define immutable security boundary contracts, not HTTP endpoint payloads.

No OpenAPI, Swagger, protobuf, or GraphQL specification was found. Jackson is used for JSON serialization and deserialization. The proposed dashboard overview DTO must be a Spring Boot composition DTO and must not become the owner of behavioral intelligence entities.

## Communication Patterns

### HTTP transport and completion semantics

- The React frontend performs HTTP GET requests to relative Spring Boot `/api` paths and rejects non-JSON or non-success responses.
- Spring Boot uses request/response HTTP transport through Java `HttpClient`, targeting `POST {prism.flask.base-uri}/analyze-event`.
- `FlaskGatewayPort` exposes completion as `CompletableFuture<JsonNode>`, so the Java integration is asynchronous at the application API boundary even though the underlying transport is HTTP request/response.
- The Flask request includes `Authorization`, `Content-Type`, `Accept`, `Request-ID`, `Correlation-ID`, and `Timestamp` headers.
- The configured Flask timeout is 30 seconds.

The root Flask endpoint validates JSON and four required feature fields, then returns `input_event`, individual raw and normalized model scores, `final_score`, `risk_level`, and `recommended_action`. Its `save_event(response)` persistence call is currently commented out, so the endpoint does not establish persisted event history for dashboard retrieval.

### Retry and failure handling

- Transport timeouts, connection failures, and downstream HTTP 5xx responses are conditionally retryable and conditionally eligible for failover.
- Authentication, authorization, validation, protocol, and invalid-response failures are not retryable.
- Retry execution is enabled only when the idempotency policy permits it; the current resilient gateway supplies a maximum of three attempts.
- The retry executor applies a configured delay, but no concrete delay value is configured in the current properties.
- No circuit-breaker implementation was found. The existing failover policy is an allow/deny decision, not a circuit-breaker state machine.
- No message broker, asynchronous event transport, service discovery client, or API gateway product was found.

### Ownership and aggregation boundary

The future dashboard composition layer belongs in Spring Boot. It should aggregate Spring-owned enterprise, project, alert, and recovery data with intelligence data obtained through an approved Flask service contract. Flask remains the owner of behavioral events, patterns, profiles, similarity, drift, confidence, predictions, and decisions. React owns presentation, filters, pagination state, and chart rendering.

The current Spring Boot source tree contains no dashboard aggregation service, repository, MongoDB adapter, typed Flask intelligence contract, or persistence-backed event retrieval operation. Although the root Flask application imports `save_event`, its call is commented out. Event analysis exists, but persisted event history is not established by the current endpoint. The dashboard must therefore represent unavailable data as unavailable rather than as zero until those contracts exist.

### Proposed dashboard overview composition

`GET /api/v1/dashboard/overview` is a proposed Spring Boot composition endpoint, not an implemented route. Its proposed response data includes:

| Field | Proposed information |
|---|---|
| `events` | Event count in the selected time window |
| `patterns` | Learned pattern statistics |
| `anomalies` | Anomaly counts |
| `blockedRisks` | Prevented high-risk operations |
| `recoveries` | Recovery counts and outcomes |
| `systemHealth` | Verified service availability |
| `asOf` | Time at which the summary was prepared |

Exact types, source mappings, time-window semantics, and freshness rules remain to be specified. Each metric must distinguish unavailable data from a genuine zero.

### Security posture

No Spring Security dependency, controller authentication filter, TLS configuration, or endpoint authorization annotation was found. A service credential provider exists at the Flask integration boundary and supplies an outbound `Authorization` header, but the credential implementation is not an HTTP API authentication mechanism. The authorization service is a contract placeholder with no policy enforcement in its default implementation.

## Service Technology Matrix

| Service | Web | Data Access | Discovery | Gateway | Actuator | Cache | Metrics |
|---|---|---|---|---|---|---|---|
| `prism-backend` | Spring MVC | No repository implementation found | None | Custom Flask HTTP client | Spring Boot Actuator | None found | No custom metrics found |
| `flask-gateway` | Flask at repository root `app.py` | Persistence call imported but disabled | None configured | Downstream intelligence boundary | Not observable | Not observable | Not observable |
| PRISM React frontend | React with Vite | None | None | Uses Spring Boot `/api` boundary | None | In-memory health state only | None |

## Service Communication Sequence

<!-- mermaid-checked: every participant uses `participant Id as "Label"`, no \n in aliases/messages/notes, every alt/opt/loop closed by end, no `:` inside any alias -->
~~~mermaid
sequenceDiagram
    participant Client as "React Dashboard"
    participant Backend as "Spring Boot Backend"
    participant Controller as "Health Controller"
    participant Flask as "Flask Intelligence Service"

    Client->>Backend: GET /api/health
    Backend->>Controller: Dispatch health request
    Controller-->>Backend: ApiResponseEnvelope health data
    Backend-->>Client: 200 JSON health envelope

    Backend->>Flask: POST /analyze-event over HTTP
    alt Flask service available
        Flask-->>Backend: JSON analysis object
        Backend-->>Backend: Complete CompletableFuture with JsonNode
    else Timeout or connection failure
        Backend-->>Backend: Apply retry or failover policy
    end
~~~
