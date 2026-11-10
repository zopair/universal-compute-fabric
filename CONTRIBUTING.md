# Contributing

- Separate control-plane decisions from data-plane transport and workload execution.
- Prefer typed contracts, deterministic behavior, explicit failure modes and small interfaces.
- A placement proposal is not proof that a workload started or completed.
- Do not add transparent WAN-backed process memory.
- Add tests for scoring, eligibility, validation and failures.
- Never commit secrets or sensitive logs.

Checks:
```bash
python -m pip install -e "services/control-plane[dev]"
ruff check services tests
pytest
```

PRs should include problem, design trade-offs, security impact, tests, observability and compatibility notes.
