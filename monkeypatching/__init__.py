from ._monkeypatching import (
    monkeypatch_module_object,
    monkeypatch_setattr,
    override_globals_during_function_call,
    NoPatchTargetsFoundError,
    InMemoryModuleError,
    CannotPatchGlobalsError,
)
