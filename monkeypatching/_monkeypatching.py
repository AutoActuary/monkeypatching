from typing import Dict, Tuple, List, Any, Union, Callable, Mapping
from pathlib import Path
from types import SimpleNamespace


def _is_subpath(child_path: Path, parent_path: Path) -> bool:
    """
    Check if one path is a subpath of another.

    Args:
        child_path: The child path to check.
        parent_path: The parent path to check against.

    Returns:
        True if child_path is a subpath of parent_path, False otherwise.
    """
    try:
        child_path.relative_to(parent_path)
        return True
    except ValueError:
        return False


def _module_base(module: Any) -> Union[None, Path]:
    """
    Retrieve the directory path or file path of a module.

    Args:
        module: The module whose file path is to be retrieved.

    Returns:
        The directory path or file path of the module if the module is
        loaded from a file structure, otherwise None.
    """
    try:
        path = Path(module.__file__).resolve()

        if path.name.lower() == "__init__.py":
            return path.parent
        else:
            return path
    except AttributeError:
        return None


class InMemoryModuleError(Exception):
    pass


def _find_submodules(module: Any) -> Dict[Path, Any]:
    """
    Recursively find all submodules from a given module. In this context, a submodule is
    defined as any attribute on the module, with the condition that the attribute has
    it's own __file__ attribute and that the __file__ subpath of the module's location.

    Args:
        module: The parent module to search from.

    Returns:
        A dictionary mapping file paths to module objects.

    Raises:
        monkeypatching.InMemoryModuleError: If the module is not loaded from
        a file structure with `.py` files.
    """
    path_to_module_map = {}

    upper_path = _module_base(module)
    if upper_path is None:
        raise InMemoryModuleError(
            "Module must be loaded from a file structure with `.py` files "
            "to robustly apply recursive patching. Use monkeypatch_setattr "
            "as an alternative for in-memory modules."
        )

    def recurse(module):
        path = _module_base(module)
        if (
            (path is None)
            or (path in path_to_module_map)
            or not _is_subpath(path, upper_path)
        ):
            return

        path_to_module_map[path] = module

        for attr_name in dir(module):
            try:
                attr = getattr(module, attr_name)
            except Exception:
                continue

            recurse(attr)

    recurse(module)
    return path_to_module_map


_list_monkeypatch_locations_cache = {}


def _list_monkeypatch_locations(
    module: Any, obj: Any, cached=False
) -> List[Tuple[Any, str]]:
    """
    List all locations where a given object is used in a module.

    Args:
        module: The module in which to search for the object.
        obj: The object to look for.
        cached: Whether to cache the monkeypatch locations; default is False.

    Returns:
        A list of tuples containing module and attribute name.
    """
    locations = None

    if cached:
        path = _module_base(module)
        if path is not None:
            if (path, id(obj)) not in _list_monkeypatch_locations_cache:
                locations = _find_submodules(module)
                _list_monkeypatch_locations_cache[(path, id(obj))] = locations

    if locations is None:
        locations = _find_submodules(module)

    f_locations = []
    for _, module in locations.items():
        for attr_name in dir(module):
            if getattr(module, attr_name) is obj:
                f_locations.append((module, attr_name))

    return f_locations


class NoPatchTargetsFoundError(Exception):
    pass


class monkeypatch_module_object:
    """
    Temporarily or permanently replace an object within a module and all its submodules.

    This can be used as a context manager with a `with` statement for temporary effect or
    can be used standalone for permanent effect.

    Args:
        module: The module in which to perform the monkeypatching.
        obj_original: The object that will be temporarily replaced.
        obj_replacement: The object that will replace `obj_original`.
        cached: Whether to cache the monkeypatch locations; default is False
                (recalculation). Warning, this is only correct if you are sure that the
                monkeypatch locations are still intact and that the object has not
                been replaced elsewhere in the code.

    Raises:
        monkeypatching.PatchTargetsNotFoundError: If no monkeypatch locations are found for
            the object in the module.
        monkeypatching.InMemoryModuleError: If the module is not loaded from a file
            structure with `.py` files.
    """

    def __init__(
        self,
        module: Any,
        obj_original: Any,
        obj_replacement: Any,
        cached: bool = False,
    ) -> None:
        monkeypatch_locations = _list_monkeypatch_locations(
            module, obj_original, cached
        )

        if len(monkeypatch_locations) == 0:
            raise NoPatchTargetsFoundError(
                f"No monkeypatch locations found for `{obj_original}` in `{module}`."
            )

        for submodule, attr_name in monkeypatch_locations:
            setattr(submodule, attr_name, obj_replacement)

        # Store for later use
        self._obj_original = obj_original
        self._monkeypatch_locations = monkeypatch_locations

    def __enter__(self) -> None:
        pass

    def __exit__(self, *args: Any) -> None:
        for submodule, attr_name in self._monkeypatch_locations:
            setattr(submodule, attr_name, self._obj_original)


class monkeypatch_setattr:
    """
    Temporarily or permanently replace an attribute within a module.

    This can be used as a context manager with a `with` statement for temporary effect or
    can be used standalone for permanent effect.

    Args:
        module: The module in which to perform the attribute replacement.
        attr_name: The attribute name that will be temporarily replaced.
        obj_replacement: The object that will replace the attribute specified by `attr_name`.
    """

    def __init__(
        self,
        module: Any,
        attr_name: str,
        obj_replacement: Any,
    ) -> None:
        self._obj_original = getattr(module, attr_name)

        setattr(module, attr_name, obj_replacement)

        self._module = module
        self._attr_name = attr_name

    def __enter__(self) -> None:
        pass

    def __exit__(self, *args: Any) -> None:
        setattr(self._module, self._attr_name, self._obj_original)


def _get_namespace_mapping(
    namespace: Union[Mapping, SimpleNamespace, Any, None]
) -> Dict:
    """
    Pass Mappings and dict through, and convert other namespace like objects to a
    dictionary of its attributes.

    Args:
        namespace: The namespace to convert, which can be a mapping, a SimpleNamespace,
        or any object that has a __dict__.

    Returns:
        A dictionary representation of the namespace.
    """
    if namespace is None:
        return {}
    elif isinstance(namespace, Mapping):
        return dict(namespace)
    else:
        return vars(namespace)


class CannotPatchGlobalsError(Exception):
    pass


class override_globals_during_function_call:
    """
    Temporarily overrides global variables of a function during the execution of that function
    call, with options for doing this for each instance of the function across a module. This
    functionality can be used as a context manager with a `with` statement or directly.

    Args:
        module: The module containing the function whose global variables are to be overridden during
                    a function call.
        function_name: The name of the function within the module for which the global variables
                    are to be overridden.
        replacements: A `Mapping`, or object with a `__dict__` attribute specifying the global variables
                    to be overridden.
        module_wide: If True, the replacement affects the module level globally, altering the function's
                    behavior everywhere it is used within the module. If False, the replacement is applied
                    only at that specific place in the module. See `monkeypatch_module_object` for a better
                    understanding.
        module_wide_cached: If True and `module_wide` is also True, caches all the locations where the original
                            function is referenced for performance optimization. This should only be used if
                            you're certain that the module's structure remain unchanged during the patch's
                            lifetime. Default is False.

    Raises:
        CannotPatchGlobalsError: If the specified function does not have a `__globals__` attribute, indicating it
                                cannot have its globals modified in this manner.

    Example usage:
        >>> pi = 3
        >>> class PretendModule:
        ...     @staticmethod
        ...     def get_tau():
        ...         return 2 * pi

        >>> with override_globals_during_function_call(PretendModule, 'get_tau', {'pi': 3.14159265358979}):
        ...     print(PretendModule.get_tau())
        6.28318530717958

        >>> print(PretendModule.get_tau())
        6
    """

    def __init__(
        self,
        module: Any,
        function_name: str,
        replacements: Union[Mapping, SimpleNamespace, Any, None],
        module_wide: bool = False,
        module_wide_cached: bool = False,
    ):

        self.replacements = _get_namespace_mapping(replacements)
        original_function = getattr(module, function_name)

        if not hasattr(original_function, "__globals__"):
            raise CannotPatchGlobalsError(
                "Object does not have a '__globals__' attribute."
            )

        self.wrapper_function = self._create_wrapper_function(original_function)

        self.monkeypatch_holder: Union[
            None, monkeypatch_module_object, monkeypatch_setattr
        ] = None

        if module_wide:
            self.monkeypatch_holder = monkeypatch_module_object(
                module,
                original_function,
                self.wrapper_function,
                cached=module_wide_cached,
            )
        else:
            self.monkeypatch_holder = monkeypatch_setattr(
                module, function_name, self.wrapper_function
            )

    def _create_wrapper_function(self, func: Callable):
        def wrapper(*args, **kwargs):
            NOVALUE = object()
            glob = func.__globals__
            reps = self.replacements
            diff = {key: glob.get(key, NOVALUE) for key in reps}

            glob.update(reps)

            try:
                return func(*args, **kwargs)
            finally:
                for key, val in diff.items():
                    if val is NOVALUE:
                        glob.pop(key, None)
                    else:
                        glob[key] = val

        return wrapper

    def __enter__(self):
        self.monkeypatch_holder.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monkeypatch_holder.__exit__(exc_type, exc_val, exc_tb)
