import unittest

from research.m5.m3_grid_crown_replay import expected_return
from research.m5.m5_source_union_replay import (
    adjusted_grid, expected_settlement_return, settlement_distribution,
    temperature_adjust,
)


class SettlementTemperatureTests(unittest.TestCase):
    def setUp(self):
        self.grid=[[0.0]*15 for _ in range(15)]
        self.grid[0][0]=0.08
        self.grid[1][0]=0.20
        self.grid[1][1]=0.14
        self.grid[2][0]=0.16
        self.grid[2][1]=0.18
        self.grid[2][2]=0.10
        self.grid[3][0]=0.14

    def test_temperature_one_preserves_distribution_and_ev(self):
        for market,side,line,price in [('AH','home',0.0,1.91),('OU','over',2.5,1.88)]:
            dist=settlement_distribution(self.grid,market,side,line)
            adjusted=temperature_adjust(dist,1.0)
            self.assertAlmostEqual(sum(adjusted.values()),1.0)
            self.assertAlmostEqual(expected_settlement_return(adjusted,price),
                                   expected_return(self.grid,market,side,line,price),places=10)

    def test_adjusted_grid_preserves_mass_and_target_category_marginals(self):
        raw=settlement_distribution(self.grid,'AH','home',0.25)
        calibrated=temperature_adjust(raw,2.0)
        grid=adjusted_grid(self.grid,'AH','home',0.25,raw,calibrated)
        self.assertAlmostEqual(sum(map(sum,grid)),1.0,places=10)
        actual=settlement_distribution(grid,'AH','home',0.25)
        self.assertEqual({k for k,v in actual.items() if v>0},{k for k,v in calibrated.items() if v>0})
        for key,value in calibrated.items():
            self.assertAlmostEqual(actual.get(key,0.0),value,places=10)

    def test_temperature_requires_valid_positive_mass(self):
        d=temperature_adjust({'win':0.4,'loss':0.6},2.0)
        self.assertAlmostEqual(sum(d.values()),1.0)
        self.assertGreater(d['win'],0.4)


if __name__=='__main__':
    unittest.main()
