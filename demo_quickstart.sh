uv run python -m aicodeagent.functions.internal.clear_output_dirs

uv run aicodeagent "Analyze the calculator app and if needed propose fixes" --demo

RUN_DIR=$(ls -td __ai_outputs__/run_* | head -n 1)
echo "=== ACTION LOG ==="
cat "$RUN_DIR/actions.log"

echo "To apply the proposed fix, run:"
echo "  uv run aicodeagent 'Apply last approved proposal' --demo"
