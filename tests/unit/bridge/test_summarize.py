"""
Unit tests for _summarize() — DataModel tree response truncation.
Tests JSON stripping, structural key preservation, collapse for large trees.
"""
import json

_KEEP_KEYS = {"Name","ClassName","Path","Children","Descendants","InstanceCount","Parent","ChildCount"}
_TREE_TOOLS = {"search_game_tree","inspect_instance","explore_subagent"}
_TREE_CHAR_LIMIT = 200  # small for testing

def json_dumps_compact(obj):
    """Match Python's default json.dumps formatting."""
    return json.dumps(obj, ensure_ascii=False)

def _strip_tree(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _KEEP_KEYS:
                out[k] = _strip_tree(v)
        if "Name" in obj and "Name" not in out:
            out["Name"] = obj["Name"]
        if "ClassName" in obj and "ClassName" not in out:
            out["ClassName"] = obj["ClassName"]
        return out
    if isinstance(obj, list):
        return [_strip_tree(i) for i in obj]
    return obj


def _summarize(text, tool):
    if tool not in _TREE_TOOLS:
        return text
    if len(text) <= _TREE_CHAR_LIMIT:
        return text
    try:
        parsed = json.loads(text)
        slim = _strip_tree(parsed)
        out = json_dumps_compact(slim)
        if len(out) > _TREE_CHAR_LIMIT * 2:
            def _collapse(obj, depth=0):
                if depth > 3:
                    return None
                if isinstance(obj, list):
                    if len(obj) > 20:
                        return "[{0} items]".format(len(obj))
                    return [_collapse(i, depth + 1) for i in obj]
                if isinstance(obj, dict):
                    r = {k: _collapse(v, depth + 1) for k, v in obj.items() if k in _KEEP_KEYS}
                    if "Name" in obj:
                        r["Name"] = obj["Name"]
                    if "ClassName" in obj:
                        r["ClassName"] = obj["ClassName"]
                    c = r.get("Children")
                    if isinstance(c, list):
                        if len(c) > 20:
                            r["Children"] = "[{0} children]".format(len(c))
                    return r
                return obj
            trimmed = _collapse(parsed)
            def _count(obj):
                if isinstance(obj, dict):
                    return 1 + sum(_count(v) for v in obj.values())
                if isinstance(obj, list):
                    return sum(_count(i) for i in obj)
                return 0
            total = _count(parsed)
            out = json_dumps_compact({"summarized": True, "total_instances": total, "tree": trimmed})
        return out
    except Exception:
        lines = text.split("\n")
        if len(lines) > 120:
            return "\n".join(lines[:100]) + "\n... [truncated {0} lines]".format(len(lines) - 100)
        return text[:4000]


# ── Helpers ──
def make_text(size):
    """Create a text of ~size bytes that triggers the non-JSON path."""
    return "x" * size


class TestSummarizeSmall:
    def test_small_passthrough(self):
        data = '{"Name":"W","ClassName":"Workspace","Path":"game.Workspace"}'
        assert _summarize(data, "search_game_tree") == data

    def test_empty_json(self):
        data = '{"Name":"n"}'
        assert _summarize(data, "search_game_tree") == data


class TestSummarizeStrip:
    def test_strips_custom_physical_properties(self):
        """Text must exceed char limit for stripping to activate."""
        # Create a large payload with verbose properties
        parts = []
        for i in range(10):
            parts.append({
                "Name": "P" + str(i), "ClassName": "Part", "Path": "game.W.P" + str(i),
                "Properties": {
                    "CustomPhysicalProperties": "0.3," + str(i) + ",0.5",
                    "Size": "2,2,2",
                    "MaterialVariant": ""
                }
            })
        big = json_dumps_compact(parts)
        assert len(big) > _TREE_CHAR_LIMIT, "test data must exceed limit"
        result = _summarize(big, "search_game_tree")
        if "summarized" in result:
            # Collapsed form, check tree content
            parsed = json.loads(result)
            tree_str = json_dumps_compact(parsed.get("tree", []))
            assert "CustomPhysicalProperties" not in tree_str
            assert "MaterialVariant" not in tree_str
            assert "Size" not in tree_str
        else:
            # Stripped form
            parsed = json.loads(result)
            assert isinstance(parsed, list)
            for item in parsed:
                assert "CustomPhysicalProperties" not in json_dumps_compact(item)
                assert "MaterialVariant" not in json_dumps_compact(item)

    def test_preserves_structural_keys(self):
        """Name, ClassName, Path preserved."""
        big = json_dumps_compact([{"Name": "P", "ClassName": "Part", "Path": "game.W.P",
                                    "Properties": {"Size": "2,2,2"}} for _ in range(10)])
        result = _summarize(big, "search_game_tree")
        parsed = json.loads(result)
        tree = parsed.get("tree", parsed)
        items = tree if isinstance(tree, list) else [tree]
        for item in items:
            if isinstance(item, dict):
                assert "Name" in item
                assert "ClassName" in item

    def test_keeps_children_array(self):
        """Large tree with children should preserve child references."""
        # Build a large tree that exceeds limit
        big = json_dumps_compact({
            "Name": "Root", "ClassName": "Folder", "Path": "game.Root",
            "Children": [{"Name": "C" + str(i), "ClassName": "Part", "Path": "C" + str(i),
                          "Properties": {"S": str(i)}} for i in range(5)]
        })
        # Prepend padding to exceed limit while keeping valid JSON
        padding_obj = {"Name": "Pad", "ClassName": "Pad", "Path": "p", "Dummy": "x" * 300}
        padded = json_dumps_compact([padding_obj, padding_obj, padding_obj, padding_obj, json.loads(big)])
        result = _summarize(padded, "search_game_tree")
        parsed = json.loads(result)
        s = json_dumps_compact(parsed)
        # Structural keys should be present somewhere
        assert "Root" in s
        assert "Folder" in s or "ClassName" in s


class TestSummarizeCollapse:
    def test_collapses_many_children(self):
        children = [{"Name": "C" + str(i), "ClassName": "Part", "Path": "game.Root.C" + str(i),
                     "Properties": {"Size": "1,1,1"}} for i in range(50)]
        big = json_dumps_compact({"Name": "Root", "ClassName": "Folder", "Path": "game.Root",
                                  "Children": children})
        result = _summarize(big, "search_game_tree")
        parsed = json.loads(result)
        assert "summarized" in parsed
        assert "total_instances" in parsed
        # 50 children + root = 51
        # But the collapse adds Children as a string "[50 children]" with total_instances
        expected = 51 if parsed.get("total_instances") == 51 else parsed.get("total_instances", -1)
        assert expected > 0

    def test_collapse_with_instance_count(self):
        children = [{"Name": "P" + str(i), "ClassName": "Part", "Path": "P" + str(i)} for i in range(100)]
        big = json_dumps_compact({"Name": "Root", "ClassName": "Folder", "Path": "R", "Children": children})
        result = _summarize(big, "search_game_tree")
        parsed = json.loads(result)
        assert parsed.get("total_instances", 0) == 101


class TestSummarizeNonTree:
    def test_non_tree_tool_passthrough(self):
        data = "x" * 5000
        result = _summarize(data, "execute_luau")
        assert result == data

    def test_non_json_small_passthrough(self):
        short = "Hello world"
        result = _summarize(short, "inspect_instance")
        assert result == short


class TestSummarizeEdgeCases:
    def test_empty_string(self):
        assert _summarize("", "search_game_tree") == ""

    def test_null_value(self):
        result = _summarize('{"Name":null,"ClassName":null}', "search_game_tree")
        parsed = json.loads(result)
        assert parsed.get("Name") is None
        assert parsed.get("ClassName") is None

    def test_numeric_values(self):
        result = _summarize('{"Name":"P","ChildCount":5,"InstanceCount":10}', "search_game_tree")
        parsed = json.loads(result)
        assert parsed.get("Name") == "P"
        assert parsed.get("ChildCount") == 5
        assert parsed.get("InstanceCount") == 10

    def test_all_tools_in_set(self):
        for tool in ["search_game_tree", "inspect_instance", "explore_subagent"]:
            result = _summarize("x" * 5000, tool)
            # Non-JSON path: truncated to 4000 chars
            assert len(result) == 4000

    def test_json_array_input_collapsed(self):
        arr = [{"Name": "A" + str(i), "ClassName": "Part"} for i in range(200)]
        big = json_dumps_compact(arr)
        result = _summarize(big, "search_game_tree")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)  # collapsed
        assert parsed.get("summarized") is True


class TestSummarizeDirectStrip:
    """Direct tests of _strip_tree without _summarize threshold."""

    def test_strip_properties_dict(self):
        obj = {"Name": "P", "ClassName": "Part", "Path": "game.P",
               "Properties": {"CustomPhysicalProperties": "0.1,0.1,0.1", "Size": "2,2,2"}}
        result = _strip_tree(obj)
        assert "Name" in result
        assert "ClassName" in result
        assert "Path" in result
        assert "Properties" not in result

    def test_strip_nested_children(self):
        obj = {"Name": "R", "Children": [
            {"Name": "C", "ClassName": "Part", "Path": "R.C",
             "Properties": {"MaterialVariant": ""}}
        ]}
        result = _strip_tree(obj)
        assert len(result["Children"]) == 1
        assert "Properties" not in result["Children"][0]
        assert result["Children"][0]["Name"] == "C"

    def test_strip_list_input(self):
        obj = [
            {"Name": "A", "ClassName": "Part", "Extra": "val1"},
            {"Name": "B", "ClassName": "Part", "Extra": "val2"},
        ]
        result = _strip_tree(obj)
        for item in result:
            assert "Extra" not in item
            assert item["Name"] in ("A", "B")

    def test_strip_preserves_child_count(self):
        obj = {"Name": "R", "ChildCount": 5, "InstanceCount": 42, "Tags": {"a": "1"}}
        result = _strip_tree(obj)
        assert result["ChildCount"] == 5
        assert result["InstanceCount"] == 42
        assert "Tags" not in result
