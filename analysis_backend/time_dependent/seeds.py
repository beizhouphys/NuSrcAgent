"""Stable global trial indices, independent of CPU layout and batch size."""


def trial_seed(base_seed: int, trial_index: int) -> int:
    if base_seed < 0 or trial_index < 0:
        raise ValueError('base seed and trial index must be non-negative')
    seed = base_seed + trial_index
    if seed > 2**32 - 1:
        raise ValueError('base seed plus trial index exceeds the uint32 seed range')
    return seed
