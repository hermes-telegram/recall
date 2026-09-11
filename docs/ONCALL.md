# On-Call Rotation

## Overview

This document outlines the on-call rotation for recall-cache.

## Rotation Schedule

| Week | Primary | Secondary |
|------|---------|-----------|
| Week 1 | @alice | @bob |
| Week 2 | @bob | @charlie |
| Week 3 | @charlie | @alice |
| Week 4 | @alice | @bob |

## Responsibilities

### Primary On-Call

- Respond to alerts within 15 minutes (P0) or 30 minutes (P1)
- Acknowledge incidents
- Mitigate issues
- Escalate if needed

### Secondary On-Call

- Backup for primary
- Take over if primary is unavailable
- Assist with complex issues

## Handoff Procedures

1. **Daily**: Review open incidents
2. **Weekly**: Formal handoff meeting
3. **After incident**: Update runbook

## Tools

| Tool | Purpose |
|------|---------|
| PagerDuty | Alerting |
| Slack #on-call | Communication |
| Grafana | Monitoring |
| Runbook | Procedures |

## Compensation

| Day | Rate |
|-----|------|
| Weekday | $100/day |
| Weekend | $200/day |
| Holiday | $300/day |
