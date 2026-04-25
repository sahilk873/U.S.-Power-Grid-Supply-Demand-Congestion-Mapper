import pandas as pd

from etl.transform.reconcile import EntityReconciler


class TestEntityReconciler:
    def setup_method(self):
        self.reconciler = EntityReconciler()

    def test_reconcile_ba_code_canonical(self):
        assert self.reconciler.reconcile_ba_code("PJM") == "PJM"

    def test_reconcile_ba_code_alias(self):
        assert self.reconciler.reconcile_ba_code("pjm interconnection") == "PJM"
        assert self.reconciler.reconcile_ba_code("California ISO") == "CAISO"
        assert self.reconciler.reconcile_ba_code("new york iso") == "NYISO"

    def test_reconcile_ba_code_unknown_passthrough(self):
        assert self.reconciler.reconcile_ba_code("UNKNOWN_BA") == "UNKNOWN_BA"

    def test_map_ba_to_iso(self):
        assert self.reconciler.map_ba_to_iso("PJM") == "PJM"
        assert self.reconciler.map_ba_to_iso("CISO") == "CAISO"
        assert self.reconciler.map_ba_to_iso("ERCOT") == "ERCOT"

    def test_reconcile_fuel_type_renewable(self):
        fuel, cat = self.reconciler.reconcile_fuel_type("Solar")
        assert cat == "renewable"

    def test_reconcile_fuel_type_thermal(self):
        fuel, cat = self.reconciler.reconcile_fuel_type("Natural Gas")
        assert cat == "thermal"

    def test_reconcile_fuel_type_other(self):
        fuel, cat = self.reconciler.reconcile_fuel_type("battery storage")
        assert cat == "other"

    def test_reconcile_ba_column_applied(self):
        df = pd.DataFrame(
            {"balancing_authority_code": ["pjm interconnection", "caiso"]}
        )
        result = self.reconciler.reconcile_ba_column(df)
        assert result["balancing_authority_code"].iloc[0] == "PJM"
        assert result["balancing_authority_code"].iloc[1] == "CAISO"

    def test_assign_iso_region_id(self):
        df = pd.DataFrame({"balancing_authority_code": ["PJM", "CISO"]})
        iso_map = {"PJM": 1, "CAISO": 2}
        result = self.reconciler.assign_iso_region_id(df, iso_map=iso_map)
        assert result["iso_region_id"].iloc[0] == 1
        assert result["iso_region_id"].iloc[1] == 2

    def test_reconcile_state_code(self):
        assert self.reconciler.reconcile_state_code("  pa ") == "PA"
        assert self.reconciler.reconcile_state_code(None) == ""
