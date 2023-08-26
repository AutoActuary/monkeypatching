# Monkeypatching

This package is designed for temporary, recursive [monkeypatching](https://en.wikipedia.org/wiki/Monkey_patch). That is to replace an object within a module with another object, across the entire module hierarchy. With this package, you can temporarily change a deeply nested behaviour in a module across the whole module.

## Why recursive monkeypatching?

Python modules are often structured to import functions from nested submodules. If you need to monkeypatch a function, it's often not sufficient to simply patch it at its function definition, since the function can persist from other import expressions. For example, if `module.submodule.function` is used within `module.othersubmodule` and is imported as:

```python
from .submodule import function
```

Patching `module.submodule.function` won't replace `module.othersubmodule.function` and won't affect its usage. Recursive monkeypatching, however, ensures that the object is replaced throughout the module hierarchy.

## Why temporary monkeypatching?


Monkeypatching can introduce ambiguity and result in unpredictable behavior. When you modify an object in an imported module, this change affects not only the current scope but also any other modules that rely on it. Such alterations can lead to unintended consequences and complicate system maintenance and debugging.

However, in the context of temporary monkeypatching, you can alter a module's behavior for a specific scope without affecting the underlying implementation. This is analogous to class inheritance, where a subclass can extend functionality without modifying the parent class.

With temporary monkeypatching, as soon as you exit the context (e.g., a `with` block), the original behavior is restored, minimizing the chances of unintended ripple effects across your codebase.

## Installation

To install Monkeypatching, use:

```bash
pip install monkeypatching
```

## Usage

### Temporary attribute replacement

Specific attributes within a module can temporarily be replaced using `monkeypatch_setattr`:

```python
from monkeypatching import monkeypatch_setattr
import json

def mock_loads(data, *args, **kwargs):
    return {"mocked": True}

with monkeypatch_setattr(json, "loads", mock_loads):
    print(json.loads('{"key": "value"}'))  # Output: {"mocked": True}
```

### Temporary module patching

An example of temporary monkeypatching:

```python
from monkeypatching import monkeypatch_module_object
import json
from json import dumps

def mock_dumps(data, *args, **kwargs):
    kwargs['indent'] = 4  # Force indentation to 4 characters
    return dumps(data, *args, **kwargs)

# Monkeypatch json.dumps in the json module and submodules
with monkeypatch_module_object(json, json.dumps, mock_dumps):
    print(json.dumps({"key": "value"}))  
    # Output: "{\n    \"key\": \"value\"\n}"

# After the block, json.dumps reverts to its original
print(json.dumps({"key": "value"}))  # Output: "{\"key\": \"value\"}"
```

### Permanent module patching

For a lasting effect:

```python
from monkeypatching import monkeypatch_module_object
import json

monkeypatch_module_object(json, json.dumps, mock_dumps)
print(json.dumps({"key": "value"}))  
# Output: "{\n    \"key\": \"value\"\n}"
```

### Caching

For repeated monkeypatching at identical locations:

```python
# With caching enabled
with monkeypatch_module_object(json, json.dumps, mock_dumps, cached=True):
    print(json.dumps({"key": "value"}))  
    # Output: "{\n    \"key\": \"value\"\n}"
```

> **Caution**: Activate caching only if monkeypatch locations remain consistent and the object hasn't been replaced elsewhere.

## API documentation

### `monkeypatch_module_object(module, obj_original, obj_replacement, cached=False)`

#### Parameters

* `module`: Target module.
* `obj_original`: The object that will be replaced.
* `obj_replacement`: The object that will replace `obj_original`.
* `cached`: Whether to cache the monkeypatch locations; default is `False`.

#### Returns

A context manager. Within a `with` block, `obj_original` gets temporarily replaced by `obj_replacement` across the specified `module` and submodules. Outside a `with` block, the replacement is permanent.

### `monkeypatch_setattr(module, attr_name, obj_replacement)`

#### Parameters

* `module`: Target module.
* `attr_name`: Attribute to be set via `setattr(attr_name, obj_replacement)`.
* `obj_replacement`: Replacement object.

#### Returns

A context manager. Within a `with` block, the specific attribute in the module is replaced by `obj_replacement`. Outside a `with` block, the replacement is permanent and identical to writing `setattr(attr_name, obj_replacement)`.

## Contributing

Contributions are always welcome! For bugs, features, or documentation updates, please open an issue or submit a pull request.

## License

This project is under the MIT License.

* * *

Thank you for using Monkeypatching! For more information or queries, raise an issue or reach out with a pull request.