from __future__ import annotations

import unittest

from numpy import allclose, arccos, array, cos, dot, exp, log, pi, sin, sum

from analysis_backend_cdx.catalog_cdx import TS_tot, legacy_ns_grid, legacy_stacking_weights, stacking_signal_background_pdfs


class CatalogLegacyEquivalenceTests(unittest.TestCase):
    def test_equal_and_model_weighting_match_legacy_equations(self):
        W_accs_src = array([[2.0, 4.0], [3.0, 9.0]])
        W_mdls_src = array([1.0, 2.0])

        for equal_weighting in (True, False):
            W_facs, W_facs_normd, fks = legacy_stacking_weights(W_accs_src, W_mdls_src, equal_weighting)
            expected_W_facs = W_accs_src if equal_weighting else W_accs_src*W_mdls_src.reshape(1,-1)
            expected_W_facs_normd = expected_W_facs/expected_W_facs.sum(axis=1).reshape(-1,1)
            expected_W_facs_sum = expected_W_facs.sum(axis=1)/W_accs_src.shape[1]
            expected_fks = expected_W_facs_sum/expected_W_facs_sum.sum()

            self.assertTrue(allclose(W_facs, expected_W_facs))
            self.assertTrue(allclose(W_facs_normd, expected_W_facs_normd))
            self.assertTrue(allclose(fks, expected_fks))

    def test_stacking_pdfs_match_likelihood_v4_block(self):
        RAs_src = array([0.1, 1.2])
        Decs_src = array([0.2, -0.3])
        W_facs_normd = array([[0.25, 0.75]])
        data = {
            "Nks": array([3]),
            "RAs_nu": [array([0.15, 1.0, 2.0])],
            "Decs_nu": [array([0.18, -0.2, 0.5])],
            "sgms_nu": [array([0.05, 0.08, 0.1])],
            "bkgd_pdfs_nu": [array([0.2, 0.0, 0.4])],
        }

        S_ki, B_ki, Nks1 = stacking_signal_background_pdfs(RAs_src, Decs_src, W_facs_normd, data, chunk_size=2)

        RAs_nu2D = data["RAs_nu"][0].reshape(-1,1)
        Decs_nu2D = data["Decs_nu"][0].reshape(-1,1)
        sgms_nu2D = data["sgms_nu"][0].reshape(-1,1)
        cos_ang_dis = cos(RAs_src.reshape(1,-1)-RAs_nu2D)*cos(Decs_src).reshape(1,-1)*cos(Decs_nu2D) + sin(Decs_src).reshape(1,-1)*sin(Decs_nu2D)
        ang_dis2 = arccos(cos_ang_dis.clip(-1.0, 1.0))**2
        spatial_facs = 1.0/(2.0*pi*sgms_nu2D**2)*exp(-ang_dis2/(2.0*sgms_nu2D**2))
        expected_signal = dot(spatial_facs, W_facs_normd[0])
        valid = data["bkgd_pdfs_nu"][0] > 0.0

        self.assertTrue(allclose(S_ki[0], expected_signal[valid]))
        self.assertTrue(allclose(B_ki[0], data["bkgd_pdfs_nu"][0][valid]))
        self.assertTrue(allclose(Nks1, array([2])))

    def test_total_ts_matches_likelihood_v4_direct_likelihood(self):
        fks = array([0.4, 0.6])
        S_ki = [array([0.4, 0.8]), array([0.3, 0.6, 0.9])]
        B_ki = [array([0.5, 0.5]), array([0.4, 0.4, 0.4])]
        Nks1 = array([2, 3])
        n_s = 1.25

        expected = 0.0
        for k in range(len(Nks1)):
            L_k = n_s*fks[k]/float(Nks1[k])*S_ki[k] + (1.0-n_s*fks[k]/float(Nks1[k]))*B_ki[k]
            expected += 2.0*sum(log(L_k)-log(B_ki[k]))

        self.assertAlmostEqual(TS_tot(n_s, fks, S_ki, B_ki, Nks1), float(expected), places=14)

    def test_seed_grid_matches_use_ebs_shape_and_limits(self):
        grid = legacy_ns_grid(5000.0)
        self.assertEqual(len(grid), 201)
        self.assertAlmostEqual(grid[0], 1.0)
        self.assertAlmostEqual(grid[-1], 2000.0)


if __name__ == "__main__":
    unittest.main()
