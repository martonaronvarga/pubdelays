---
title: Internals
description: Stage contracts, parser behavior, validation, performance, and error-handling details.
icon: octicons/cpu-16
---

# Internals

<div class="grid cards" markdown>

-   :octicons-workflow-16: **Pipeline internals**

    Function-level map of dispatch, parsing, transform, aggregation, and SLURM execution.

    [Pipeline](pipeline.md)

-   :octicons-file-code-16: **Parser**

    Streaming MEDLINE XML parsing behavior and edge cases.

    [Parser](parser.md)

-   :octicons-tasklist-16: **Stage contracts**

    Inputs, outputs, manifest rows, resume behavior, and empty-input rules.

    [Stage contracts](stage-contracts.md)

-   :octicons-check-circle-16: **Validation**

    Correctness checks and test commands.

    [Validation](validation.md)

-   :octicons-meter-16: **Performance**

    Benchmark procedure and throughput-sensitive boundaries.

    [Performance](performance.md)

-   :octicons-bug-16: **Error handling**

    Failure rows, malformed inputs, recovery commands, and known limits.

    [Error handling](error-handling.md)

</div>
