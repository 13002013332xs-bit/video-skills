import importlib.util
from pathlib import Path
import unittest

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('creator_pps', SKILL / 'scripts/creator_pps.py')
pps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pps)


class PPSRules(unittest.TestCase):
    def test_left_score_is_not_denominator_or_ratio(self):
        self.assertEqual(str(pps.parse_pps('PPS: 4.9 / 5.0')), '4.9')

    def test_user_example_excludes_49(self):
        self.assertEqual(pps.evaluate_pps('4.9 / 5.0', selected_scores=['4.5', '4.6', '4.7', '4.8'])['status'], 'excluded')

    def test_each_selected_score_is_eligible(self):
        for score in ['4.5', '4.6', '4.7', '4.8']:
            with self.subTest(score=score):
                self.assertEqual(pps.evaluate_pps(score+' / 5.0', selected_scores=['4.5', '4.6', '4.7', '4.8'])['status'], 'eligible')

    def test_discrete_selection_does_not_fill_holes(self):
        self.assertEqual(pps.evaluate_pps('4.6 / 5.0', selected_scores=['4.5', '4.8'])['status'], 'excluded')

    def test_range_includes_both_endpoints(self):
        for score in ['4.5', '4.6', '4.8']:
            with self.subTest(score=score):
                self.assertEqual(pps.evaluate_pps(score+' / 5.0', minimum='4.5', maximum='4.8')['status'], 'eligible')

    def test_range_excludes_outside_scores(self):
        for score in ['4.4', '4.9', '5.0']:
            with self.subTest(score=score):
                self.assertEqual(pps.evaluate_pps(score+' / 5.0', minimum='4.5', maximum='4.8')['status'], 'excluded')

    def test_missing_is_pending_not_zero(self):
        for card in [None, '-', 'PPS: - / 5.0', '5.0 / 10.0', 'other 4.9 5.0']:
            with self.subTest(card=card):
                result=pps.evaluate_pps(card, minimum='4.5')
                self.assertEqual(result['status'], 'pending')
                self.assertIsNone(result['score'])

    def test_no_pps_condition_does_not_restrict(self):
        self.assertEqual(pps.evaluate_pps('-')['status'], 'not_required')

    def test_exact_value_is_not_rounded(self):
        self.assertEqual(pps.evaluate_pps('4.55 / 5.0', selected_scores=['4.5'])['status'], 'excluded')

    def test_full_width_and_spacing(self):
        self.assertEqual(str(pps.parse_pps(' PPS： 4.8 ／ 5.0 ')), '4.8')

    def test_reversed_range_rejected(self):
        with self.assertRaises(ValueError):
            pps.evaluate_pps('4.7 / 5.0', minimum='4.8', maximum='4.5')

    def test_do_not_mix_set_and_range(self):
        with self.assertRaises(ValueError):
            pps.evaluate_pps('4.7 / 5.0', selected_scores=['4.5'], minimum='4.5')


if __name__ == '__main__':
    unittest.main(verbosity=2)
