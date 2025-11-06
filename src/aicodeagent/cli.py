import sys, runpy

def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: aicodeagent <prompt>")
        return 1
    # Passa il prompt a main.py come argv
    sys.argv = ["main.py"] + argv
    runpy.run_module("aicodeagent.main", run_name="__main__")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())