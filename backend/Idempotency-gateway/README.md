# FinSafe Idempotency Layer API

A RESTful payment-processing simulation that prevents double charging by using an `Idempotency-Key` header.

sequenceDiagram
    participant Client
    participant API
    participant Store
    participant PaymentProcessor

    Client->>API: POST /process-payment + Idempotency-Key
    API->>Store: Check key

    alt Key does not exist
        API->>PaymentProcessor: Process payment
        PaymentProcessor-->>API: Payment success
        API->>Store: Save payload hash + response
        API-->>Client: Return 201 Created
    else Same key and same body
        API->>Store: Fetch saved response
        API-->>Client: Return saved response + X-Cache-Hit true
    else Same key but different body
        API-->>Client: Return 409 Conflict
    end