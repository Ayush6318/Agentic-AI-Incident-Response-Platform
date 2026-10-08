ALL_TOOLS = {"search_logs", "get_metrics", "get_recent_commits"}

INCIDENTS = [
  {"id": "db_pool", "scenario": "db_pool",
   "text": "payment-service returns HTTP 500 and database timeouts after the latest deploy",
   "service": "payment-service",
   "expected_cause": "Database connection pool exhausted because commit abc123 increased the batch size from 100 to 1000",
   "expected_action": "rollback abc123"},

  {"id": "redis_memory", "scenario": "redis_memory",
   "text": "cache-service is slow and the cache hit ratio dropped sharply",
   "service": "cache-service",
   "expected_cause": "Redis memory exhaustion (used memory near maxmemory causing evictions)",
   "expected_action": "none"},

  {"id": "slow_query", "scenario": "slow_query",
   "text": "report-service /reports/monthly is timing out",
   "service": "report-service",
   "expected_cause": "Slow database query doing a sequential scan, likely a missing index on orders.customer_email",
   "expected_action": "none"},

  {"id": "memory_leak", "scenario": "memory_leak",
   "text": "auth-service pods keep restarting every few hours",
   "service": "auth-service",
   "expected_cause": "Memory leak causing heap usage to grow until OutOfMemoryError",
   "expected_action": "none"},

  {"id": "bad_deploy", "scenario": "bad_deploy",
   "text": "checkout-service is completely down since the 16:00 deployment",
   "service": "checkout-service",
   "expected_cause": "Failed deployment: commit xyz789 pointed the service at the wrong (old) database host",
   "expected_action": "rollback xyz789"},
]
for inc in INCIDENTS:
    inc["expected_tools"] = ALL_TOOLS