# Decision

We need an idempotency strategy for our public payment-create API so retried POSTs
never double-charge. Constraints: <50ms added p99 latency, must survive a single
region outage, team of 3, ship in two weeks. Decide between a client-supplied
idempotency key with a dedup store vs. server-derived request fingerprinting.
