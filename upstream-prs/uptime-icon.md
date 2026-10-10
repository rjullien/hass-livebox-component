Title: fix(sensor): add the mdi: prefix to the uptime sensor icon

The uptime sensor declares `icon="progress-clock"`. Home Assistant only resolves icons written as `<set>:<name>`, so this icon is never found and the sensor is shown without the intended clock icon.

```diff
- icon="progress-clock",
+ icon="mdi:progress-clock",
```

This is a one-line change and nothing else is affected.
