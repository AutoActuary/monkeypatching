import unittest
import xml
import math
from pathlib import Path
from textwrap import dedent
import os
from tempfile import TemporaryDirectory
import sys
from typing import Any
from uuid import uuid4
import locate
import doctest

with locate.prepend_sys_path(".."):
    from monkeypatching import (
        _monkeypatching,
        monkeypatch_module_object,
        monkeypatch_setattr,
        override_globals_during_function_call,
        InMemoryModuleError,
        NoPatchTargetsFoundError,
        CannotPatchGlobalsError,
    )


def load_tests(loader, tests, ignore):
    # Add doctests from your_module
    tests.addTests(doctest.DocTestSuite(_monkeypatching))
    return tests


# Your example package
example_package = {
    "__init__.py": dedent(
        """
        from .foo import a, b, c, d
        from .bar.baz import e, f
    """
    ),
    "foo.py": dedent(
        """
        from .bar import f
        def a():
            return "Function a from foo module and " + f()

        def b():
            return "Function b from foo module"

        def c():
            return "Function c from foo module"

        def d():
            return "Function d from foo module"
    """
    ),
    "bar/__init__.py": dedent(
        """
        from .baz import e, f
    """
    ),
    "bar/baz.py": dedent(
        """
        def e():
            return "Function e from bar.baz module"

        def f():
            return "Function f from bar.baz module"
    """
    ),
}


def load_random_example_package() -> Any:
    package_name = f"package_{uuid4().hex[:8]}"

    with TemporaryDirectory() as tmpdir:
        package_dir = Path(tmpdir) / package_name
        for rel_path, content in example_package.items():
            full_path = package_dir / rel_path
            os.makedirs(full_path.parent, exist_ok=True)
            full_path.write_text(content)

        sys.path.insert(0, str(tmpdir))
        exec(f"import {package_name}")

    return eval(package_name)


class TestMonkeypatching(unittest.TestCase):
    def test_temporary_replacement_with_module_object(self):
        import xml.etree.ElementTree as ET

        def mock_tostring(element, *args, **kwargs):
            return "mocked!"

        with monkeypatch_module_object(xml, ET.tostring, mock_tostring):
            self.assertEqual(ET.tostring(ET.Element("data")), "mocked!")

        self.assertNotEqual(ET.tostring(ET.Element("data")), "mocked!")

    def test_temporary_replacement_with_module_object_2(self):
        example_package = load_random_example_package()

        def mock_function_f_permanent():
            return "permanently_mocked!"

        self.assertEqual(example_package.f(), "Function f from bar.baz module")
        self.assertEqual(
            example_package.a(),
            "Function a from foo module and Function f from bar.baz module",
        )

        monkeypatch_module_object(
            example_package, example_package.bar.baz.f, mock_function_f_permanent
        )

        self.assertEqual(example_package.bar.baz.f(), "permanently_mocked!")
        self.assertEqual(
            example_package.a(), "Function a from foo module and permanently_mocked!"
        )

    def test_permanent_replacement_with_module_object(self):
        example_package = load_random_example_package()

        def mock_function_a_permanent():
            return "permanently_mocked!"

        monkeypatch_module_object(
            example_package, example_package.foo.a, mock_function_a_permanent
        )
        self.assertEqual(example_package.foo.a(), "permanently_mocked!")

    def test_cached_replacement_with_module_object(self):
        import xml.etree.ElementTree as ET

        def mock_tostring_cached(element, *args, **kwargs):
            return "cached!"

        with monkeypatch_module_object(
            xml, ET.tostring, mock_tostring_cached, cached=True
        ):
            self.assertEqual(ET.tostring(ET.Element("data")), "cached!")

        # Verify that the cache has a key (Path, int) that matches (.*ET, int)

        self.assertIn(
            (Path(xml.__file__).resolve().parent, id(ET.tostring)),
            _monkeypatching._list_monkeypatch_locations_cache,
        )

    def test_temporary_replacement_with_setattr(self):
        def mock_sin(x):
            return "mocked!"

        with monkeypatch_setattr(math, "sin", mock_sin):
            self.assertEqual(math.sin(0), "mocked!")

        self.assertEqual(math.sin(0), 0.0)

    def test_permanent_replacement_with_setattr(self):
        example_package = load_random_example_package()

        def mock_function_a_permanent():
            return "permanently_mocked!"

        monkeypatch_setattr(example_package.foo, "a", mock_function_a_permanent)
        self.assertEqual(example_package.foo.a(), "permanently_mocked!")

    def test_wrong_object_with_module_object(self):
        def mock_fake(x):
            return "fake!"

        with self.assertRaises(NoPatchTargetsFoundError):
            with monkeypatch_module_object(xml, "fake_object", mock_fake):
                pass

    def test_in_memory_module_with_module_object(self):
        import builtins

        abs = builtins.abs

        def mock_abs(x):
            return "mocked!"

        with self.assertRaises(InMemoryModuleError):
            with monkeypatch_module_object(builtins, abs, mock_abs):
                pass


global_var = "original"


class TestOverrideGlobalsDuringFunctionCall(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        # Path to the temporary module
        example_module_path = Path(self.temp_dir.name) / "mock_module.py"
        example_module_path.write_text(
            dedent(
                """
                global_var = "original value"
                
                def use_global_var():
                    return global_var
                """
            )
        )
        sys.path.insert(0, self.temp_dir.name)
        d = {}
        exec("import mock_module", d)
        self.mock_module = d["mock_module"]

    def test_override_global_var_in_function(self):
        # Ensure the function returns the original global value
        self.assertEqual(self.mock_module.use_global_var(), "original value")

        # Use override_globals_during_function_call to temporarily override the global variable
        with override_globals_during_function_call(
            self.mock_module, "use_global_var", {"global_var": "patched value"}
        ):
            self.assertEqual(self.mock_module.use_global_var(), "patched value")

        # Ensure the global variable is restored after the context manager
        self.assertEqual(self.mock_module.use_global_var(), "original value")

    def test_temporary_override_within_module(self):
        # Define a mock module and function for testing
        class MockModule:
            @staticmethod
            def test_func():
                return global_var

        # Verify initial behavior
        self.assertEqual(MockModule.test_func(), "original")

        # Apply override
        with override_globals_during_function_call(
            MockModule, "test_func", {"global_var": "temporarily overridden"}
        ):
            self.assertEqual(MockModule.test_func(), "temporarily overridden")

        # Verify behavior is restored
        self.assertEqual(MockModule.test_func(), "original")

    def test_with_invalid_function_name(self):
        # Attempt to override an undefined function
        with self.assertRaises(AttributeError):
            with override_globals_during_function_call(
                self.mock_module, "undefined_function", {"global_var": "new value"}
            ):
                pass  # The function call is expected to raise AttributeError

    def test_direct_application_without_context_manager(self):
        # Directly apply the override without a context manager
        patcher = override_globals_during_function_call(
            self.mock_module, "use_global_var", {"global_var": "directly patched value"}
        )
        try:
            self.assertEqual(
                self.mock_module.use_global_var(), "directly patched value"
            )
        finally:
            patcher.__exit__(None, None, None)

        # Ensure the override is reverted
        self.assertEqual(self.mock_module.use_global_var(), "original value")

    def test_trigger_cannot_patch_globals_error_with_math_sin(self):
        # Attempting to set 'pi' for 'math.sin' should trigger the error, since math.sin is not
        # a pure python function.
        with self.assertRaises(CannotPatchGlobalsError):
            with override_globals_during_function_call(math, "sin", {"pi": 3.14}):
                pass


if __name__ == "__main__":
    unittest.main()
