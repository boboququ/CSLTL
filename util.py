"""Random Utilities for TangyBot."""

import gzip
import pickle


def save(obj, path):
    """Save an object to a file by pickling and gziping it."""
    with gzip.open(path, 'wb') as out:
        pickle.dump(obj, out)


def load(path):
    """Load a gzipped pickled object from a file."""
    obj = None
    with gzip.open(path, 'rb') as pkl_file:
        obj = pickle.load(pkl_file)
    return obj
