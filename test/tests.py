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

with locate.prepend_sys_path(".."):
    from monkeypatching import (
        _monkeypatching,
        monkeypatch_module_object,
        monkeypatch_setattr,
        InMemoryModuleError,
        NoPatchTargetsFoundError,
    )


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


if __name__ == "__main__":
    unittest.main()
