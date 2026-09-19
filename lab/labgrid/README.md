# labgrid integration

Track D2 (#49) will use labgrid as the multi-host resource exporter/coordinator layer.

Controller v1 establishes the lower-level invariants first:

- versioned bench inventory under `lab/resources/`;
- exclusive local Linux resource locking;
- controller/backend/DUT/adapter/fieldbus identity fields;
- safe cleanup remains mandatory.

A concrete labgrid exporter/coordinator configuration should be added only after the actual power/reset/serial/interface devices on the bench are frozen; this repository does not publish a guessed hardware configuration.
