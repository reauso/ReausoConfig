"""Multirun help text for CLI integration.

This module provides the help text for multirun CLI options, which is
automatically included by built-in help integrations.
"""

MULTIRUN_HELP = """\
Multirun Options:
  -e, --experiment KEY=VAL  Define an experiment configuration (can repeat)
                            Example: -e model=resnet,lr=0.01 -e model=vit,lr=0.001

Sweep Syntax:
  KEY=VAL1,VAL2             Sweep over comma-separated values (cartesian product)
  KEY=[VAL1, VAL2]          Bracket syntax (for values containing commas)

Examples:
  python train.py model=resnet,vit optimizer.lr=0.01,0.001
  python train.py -e model=resnet -e model=vit optimizer.lr=0.01,0.001"""
