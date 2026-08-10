# Alert lifecycle

```text
SAFE → WATCH → WARNING → CRITICAL
  ▲        │        │         │
  └────────┴────────┴── RESOLVING → CLOSED
```

A severity must persist for a configurable number of updates before opening or escalation. Release
uses a lower score boundary than activation, producing hysteresis. Cooldown suppresses duplicate
notifications, while critical alerts may be repeated after a longer configured interval.
