import numpy as np
from ultralytics.utils.files import increment_path


def convert_numpy_types(data):
    if isinstance(data, dict):
        return {
            convert_numpy_types(key): convert_numpy_types(value)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [convert_numpy_types(element) for element in data]
    elif isinstance(data, tuple):
        return tuple(convert_numpy_types(element) for element in data)
    elif isinstance(data, set):
        return {convert_numpy_types(element) for element in data}
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    elif isinstance(data, np.bool_):
        return bool(data)
    elif isinstance(data, np.str_):
        return str(data)
    else:
        return data
