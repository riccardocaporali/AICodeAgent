from dataclasses import dataclass


@dataclass
class PipelineOptions:
    verbose: bool
    I_O: bool
    reset: bool
    demo: bool
