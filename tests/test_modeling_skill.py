import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'agents/modeling-design/skills/blender-reference-blockout'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.check = load(SKILL / 'scripts/check_contract.py', 'contract_check')
        self.data = json.loads((SKILL / 'assets/modeling-contract.example.json').read_text(encoding='utf-8'))

    def test_text_only_relative_scale_is_valid(self):
        before = copy.deepcopy(self.data)
        self.assertTrue(self.check.validate_contract(self.data)['valid'])
        self.assertEqual(self.data, before)

    def test_invalid_dimensions_nan_infinity_boolean_zero_negative(self):
        for value in (float('nan'), float('inf'), True, 0, -1):
            with self.subTest(value=value):
                self.data['components'][0]['dimensions']['x'] = value
                self.assertFalse(self.check.validate_contract(self.data)['valid'])

    def test_scale_cannot_claim_real_units_without_a_number(self):
        self.data['scale']['source'] = 'measured'
        self.assertFalse(self.check.validate_contract(self.data)['valid'])

    def test_unknown_parent_and_cycle_rejected(self):
        self.data['components'][0]['parent'] = 'not-present'
        self.assertFalse(self.check.validate_contract(self.data)['valid'])
        self.data['components'][0]['parent'] = 'attachment'
        self.assertFalse(self.check.validate_contract(self.data)['valid'])

    def test_missing_and_changed_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            self.data['reference_images'] = [{'id': 'shape', 'role': 'shape', 'path': 'source.bin'}]
            self.assertFalse(self.check.validate_contract(self.data, folder, True)['valid'])
            path = Path(folder) / 'source.bin'
            path.write_bytes(b'reference content fixture; not an actual image')
            self.data['reference_images'][0]['sha256'] = self.check.fingerprint_file(path)
            self.assertTrue(self.check.validate_contract(self.data, folder, True)['valid'])
            path.write_bytes(b'changed content')
            self.assertFalse(self.check.validate_contract(self.data, folder, True)['valid'])

    def test_output_escape_rejected(self):
        self.data['deliverables'] = ['../outside.blend']
        self.assertFalse(self.check.validate_contract(self.data)['valid'])

    def test_unsupported_fact_does_not_become_confirmed(self):
        self.data['facts'][0]['status'] = 'AI approved'
        self.assertFalse(self.check.validate_contract(self.data)['valid'])

    def test_malformed_components_return_errors(self):
        self.data['components'] = [None, {'id': 'bad', 'parent': []}]
        self.assertFalse(self.check.validate_contract(self.data)['valid'])


class GeometryEvidenceTests(unittest.TestCase):
    def test_bounds_arithmetic_not_an_aesthetic_test(self):
        audit = load(SKILL / 'scripts/blender_audit.py', 'bounds_audit')
        result = audit.bounds_from_points([(3, -2, 0), (-1, 4, 7), (2, 0, 2)])
        self.assertEqual(result['min'], [-1, -2, 0])
        self.assertEqual(result['max'], [3, 4, 7])
        self.assertEqual(result['dimensions'], [4, 6, 7])
        for points in ([], [(1, 2)], [(float('nan'), 0, 1)]):
            with self.assertRaises(ValueError):
                audit.bounds_from_points(points)


if __name__ == '__main__':
    unittest.main()
