"""
Unit tests for MCPM — MCP manager that indexes tools across servers.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "bridge"))
from bridge import MCPM, MCPC


class TestMCPMInit:
    def test_init_empty(self):
        m = MCPM()
        assert len(m.cl) == 0
        assert len(m.idx) == 0

    def test_init_creates_locks(self):
        m = MCPM()
        assert m.ixl is not None


class TestMCPMIndex:
    def test_rebuild_index_empty(self):
        m = MCPM()
        m._rbi()
        assert len(m.idx) == 0

    def test_rebuild_index_single_server(self):
        m = MCPM()
        from bridge import MCPC
        c = MCPC("srv1", "cmd", [])
        c.tc = [
            {"name": "tool_a", "description": "Tool A"},
            {"name": "tool_b", "description": "Tool B"},
        ]
        m.cl["srv1"] = c
        m._rbi()
        assert m.idx["tool_a"] == (c, "tool_a")
        assert m.idx["tool_b"] == (c, "tool_b")
        assert len(m.idx) == 2

    def test_rebuild_duplicate_tool_names_prefixed(self):
        m = MCPM()
        c1 = MCPC("srv1", "cmd", [])
        c1.tc = [{"name": "tool_x"}, {"name": "tool_y"}]
        c2 = MCPC("srv2", "cmd", [])
        c2.tc = [{"name": "tool_x"}, {"name": "tool_z"}]
        m.cl["srv1"] = c1
        m.cl["srv2"] = c2
        m._rbi()
        # First server's tool_x gets the short name
        assert m.idx["tool_x"] == (c1, "tool_x")
        assert m.idx["tool_y"] == (c1, "tool_y")
        # Second server's tool_x gets prefixed
        assert m.idx["srv2/tool_x"] == (c2, "tool_x")
        assert m.idx["tool_z"] == (c2, "tool_z")

    def test_rebuild_multiple_duplicates(self):
        m = MCPM()
        c1 = MCPC("a", "cmd", [])
        c1.tc = [{"name": "dup"}]
        c2 = MCPC("b", "cmd", [])
        c2.tc = [{"name": "dup"}]
        c3 = MCPC("c", "cmd", [])
        c3.tc = [{"name": "dup"}]
        m.cl["a"] = c1
        m.cl["b"] = c2
        m.cl["c"] = c3
        m._rbi()
        assert m.idx["dup"] == (c1, "dup")
        assert m.idx["b/dup"] == (c2, "dup")
        assert m.idx["c/dup"] == (c3, "dup")


class TestMCPMListTools:
    def test_list_tools_empty(self):
        m = MCPM()
        assert m.lt() == []

    def test_list_tools_preserves_insertion_order(self):
        """lt() preserves insertion order from C.tc, not sorted."""
        from bridge import MCPC
        m = MCPM()
        c = MCPC("srv", "cmd", [])
        c.tc = [
            {"name": "b_tool"},
            {"name": "a_tool"},
            {"name": "c_tool"},
        ]
        m.cl["srv"] = c
        m._rbi()
        names = [t["name"] for t in m.lt()]
        # Order is insertion order of c.tc
        assert names == ["b_tool", "a_tool", "c_tool"]

    def test_renamed_tool_uses_index_name(self):
        """When tool name collisions occur, the name from idx is used."""
        from bridge import MCPC
        m = MCPM()
        c = MCPC("srv", "cmd", [])
        c.tc = [{"name": "unique_tool"}]
        m.cl["srv"] = c
        m._rbi()
        tools = m.lt()
        assert len(tools) == 1
        assert tools[0]["name"] == "unique_tool"


class TestMCPMProbe:
    def test_any_a_no_servers(self):
        m = MCPM()
        assert not m.any_a()

    def test_any_a_with_alive_server(self):
        m = MCPM()
        c = MCPC("srv", "cmd", [])
        import unittest.mock as um
        with um.patch.object(c, "is_a", return_value=True):
            m.cl["srv"] = c
            assert m.any_a()

    def test_any_a_with_dead_server(self):
        m = MCPM()
        c = MCPC("srv", "cmd", [])
        import unittest.mock as um
        with um.patch.object(c, "is_a", return_value=False):
            m.cl["srv"] = c
            assert not m.any_a()

    def test_any_a_mixed_servers(self):
        m = MCPM()
        c1 = MCPC("a", "cmd", [])
        c2 = MCPC("b", "cmd", [])
        import unittest.mock as um
        with um.patch.object(c1, "is_a", return_value=False), \
             um.patch.object(c2, "is_a", return_value=True):
            m.cl["a"] = c1
            m.cl["b"] = c2
            assert m.any_a()
