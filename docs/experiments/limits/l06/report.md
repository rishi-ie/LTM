# L6 Report

Status: **IMPLEMENTATION IN PROGRESS**

No authoritative L6 locked result has been claimed. The current package has a
bounded smoke harness and six focused tests. The smoke path is intentionally
not the 25,000-body/8,000-query locked execution and must not be cited as an
L6 pass.

Current checks:

```text
focused tests: 6 passed
Ruff:          passed
compileall:    passed
git diff:      passed
```

The ignored 40-case smoke run produced `L6-H` with `0.20` exactness,
`0.20` accepted precision and 32 incorrect accepted smoke predictions. This is
not an authoritative L6 result; it is the expected implementation signal that
the current minimal optimizer and fixture generator must be replaced by the
trained equilibrium kernel and independent global oracle before locked scoring.

The decisive remaining work is the independent high-precision equilibrium
oracle, the full 25,000-body reality generator, trained equilibrium kernel,
immutable locked lifecycle, and causal controls proving that learned geometry
is necessary for the answer rather than merely accompanying exact propagation.
