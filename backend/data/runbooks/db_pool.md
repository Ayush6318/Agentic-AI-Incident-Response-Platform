# Database connection pool exhausted
1. Check recent deploys that changed batch size or concurrency.
2. Roll back the deploy if usage > 90% right after release.
3. Increase pool size only as a last resort.