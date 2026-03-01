# Documentation

This folder should contain your documentation, explaining the structure and content of your project. It should also contain your diagrams, explaining the architecture. The recommended writing format is Markdown.


## Recommendation Service

`recomendation_sys` now exposes a gRPC API:

- Service: `recommendation_system.RecommendationService`
- RPC: `GetRecommendations(RecommendationRequest) -> RecommendationResponse`

Proto file:

- `utils/pb/recommendation_system.proto`

### Request shape

```proto
message RecommendationRequest {
  string user_comment = 1;
  repeated OrderItem items = 2;
  int32 top_k = 3;
}
```

### Response shape

```proto
message RecommendationResponse {
  repeated RecommendedBook suggested_books = 1;
  optional string error_message = 2;
}
```

### Ranking strategy

The service is AI-only:

- It sends cart titles, user comment, and catalog to OpenAI.
- The model returns JSON with `bookId`, `reason`, and short description.
- The service validates output and returns structured gRPC messages.

