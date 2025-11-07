import runpy
import sys


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    sys.argv = ["aicodeagent.main"] + argv
    runpy.run_module("aicodeagent.main", run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
