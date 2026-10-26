# SPDX-License-Identifier: MIT
"""Use the published schema, plus runtime cross-field refusal checks."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator, ValidationError

from tools.world_package import build_plan
from tools.world_package.tests.fixtures import package, receipt


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = json.loads((Path(__file__).resolve().parents[1] / "import-plan-v1.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(schema)

    def test_new_no_op_and_explicit_receipt_validate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = package(Path(temp) / "fixture.zip")
            new = build_plan(path)
            accepted = receipt(new)
            for value in (new, accepted, build_plan(path, accepted)):
                with self.subTest(format=value["format"]):
                    self.validator.validate(value)

    def test_schema_refuses_weakened_policy_unknown_fields_and_fake_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            plan = build_plan(package(Path(temp) / "fixture.zip"))
        for field in ("native_acceptance", "extra"):
            changed = copy.deepcopy(plan)
            changed[field] = True
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.validator.validate(changed)
        for flag in ("replace_existing", "delete_existing", "use_shared_materials", "connect_live"):
            changed = copy.deepcopy(plan)
            changed["policy"][flag] = True
            with self.subTest(flag=flag), self.assertRaises(ValidationError):
                self.validator.validate(changed)
        accepted = receipt(plan)
        accepted["version"] = True
        with self.assertRaises(ValidationError):
            self.validator.validate(accepted)

    def test_schema_has_exact_signed_64_bit_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            plan = build_plan(package(Path(temp) / "fixture.zip"))
        for value in (plan, receipt(plan)):
            for number in (2 ** 63 - 1, 2 ** 63):
                changed = copy.deepcopy(value)
                if changed["format"] == "daedalus-world-import-plan":
                    changed["world"]["revision"] = number
                    changed["geometry"]["chunks"] = number
                    changed["geometry"]["triangles"] = number
                else:
                    changed["revision"] = number
                if number < 2 ** 63:
                    self.validator.validate(changed)
                else:
                    with self.assertRaises(ValidationError):
                        self.validator.validate(changed)


if __name__ == "__main__":
    unittest.main()
