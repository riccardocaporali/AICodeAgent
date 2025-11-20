#!/bin/bash

# Number of repetitions (default: 5)
RUNS=${1:-2}

echo "Running E2E tests $RUNS times..."
echo

for i in $(seq 1 $RUNS); do
    echo "----- E2E RUN $i -----"
    uv run pytest tests/e2e -q
    echo
done

echo "Done."
