"""Operational tooling for the forex trading system.

Provides CLI utilities for monitoring system health:
- check_heartbeat: detect stale/missing heartbeats from the paper-trading loop
- audit_trials: detect trials that were spawned but never completed
"""
