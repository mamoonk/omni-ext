"""
Unit tests for sc() — the synchronous dispatch point.
Tests that sc() wraps execute_luau with _wl(), applies _summarize,
and propagates errors correctly.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "bridge"))


class MockMGR:
    """Simulates MCPM.cl() for testing sc()."""
    def __init__(self):
        self.last_name = None
        self.last_args = None
        self.last_timeout = None
        self.result = {"text": "", "images": []}

    def cl(self, name, args, timeout=30):
        self.last_name = name
        self.last_args = args
        self.last_timeout = timeout
        return self.result


class TestScBasic:
    def test_sc_calls_mgr_cl(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        mock = MockMGR()
        mock.result = {"text": "ok", "images": []}
        sys.modules["bridge"].mgr = mock
        try:
            r = sc("script_read", {"path": "game.Foo"}, 30)
            assert r["ok"] is True
            assert r["text"] == "ok"
            assert mock.last_name == "script_read"
            assert mock.last_args == {"path": "game.Foo"}
        finally:
            sys.modules["bridge"].mgr = mgr_backup

    def test_sc_passes_images_through(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        mock = MockMGR()
        mock.result = {"text": "img captured", "images": [{"data": "AAAA", "mimeType": "image/png"}]}
        sys.modules["bridge"].mgr = mock
        try:
            r = sc("screen_capture", {}, 30)
            assert r["ok"] is True
            assert len(r["images"]) == 1
            assert r["images"][0]["data"] == "AAAA"
        finally:
            sys.modules["bridge"].mgr = mgr_backup


class TestScExecuteLuau:
    def test_sc_wraps_execute_luau_with_wl(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        mock = MockMGR()
        mock.result = {"text": "done", "images": []}
        sys.modules["bridge"].mgr = mock
        try:
            code = "while true do end"
            r = sc("execute_luau", {"code": code}, 30)
            assert r["ok"] is True
            # The code is wrapped in pcall() but still contains original 'while'
            assert "_zsC()" in mock.last_args["code"]
            assert "pcall(function()" in mock.last_args["code"]
            assert "_zsS=os.clock()" in mock.last_args["code"]
            assert "_zsL=15" in mock.last_args["code"]
        finally:
            sys.modules["bridge"].mgr = mgr_backup

    def test_sc_wraps_code_with_dangerous_patterns(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        mock = MockMGR()
        mock.result = {"text": "done", "images": []}
        sys.modules["bridge"].mgr = mock
        try:
            code = "repeat task.wait() until false"
            sc("execute_luau", {"code": code}, 30)
            assert "_zsC()" in mock.last_args["code"]
        finally:
            sys.modules["bridge"].mgr = mgr_backup


class TestScSummarization:
    def test_sc_summarizes_tree_responses(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        mock = MockMGR()
        big = json.dumps({"Name": "Root", "ClassName": "Folder", "Path": "game.Root",
                          "Properties": {"CustomPhysicalProperties": "x"},
                          "Children": [{"Name": "C", "ClassName": "Part", "Path": "c",
                                        "Properties": {"MaterialVariant": "y"}}]})
        # Make it exceed limit by repeating
        big = json.dumps([json.loads(big) for _ in range(100)])
        mock.result = {"text": big, "images": []}
        sys.modules["bridge"].mgr = mock
        try:
            r = sc("search_game_tree", {}, 30)
            assert r["ok"] is True
            assert "CustomPhysicalProperties" not in r["text"]
            assert "MaterialVariant" not in r["text"]
        finally:
            sys.modules["bridge"].mgr = mgr_backup

    def test_sc_does_not_summarize_non_tree(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        mock = MockMGR()
        long_text = "x" * 50000
        mock.result = {"text": long_text, "images": []}
        sys.modules["bridge"].mgr = mock
        try:
            r = sc("execute_luau", {"code": "return 1"}, 30)
            assert r["ok"] is True
            assert r["text"] == long_text  # unchanged
        finally:
            sys.modules["bridge"].mgr = mgr_backup


class TestScErrors:
    def test_sc_returns_timeout_error(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        err_mock = MockMGR()

        def timeout_cl(name, args, timeout=30):
            raise TimeoutError("timed out after 30s")

        err_mock.cl = timeout_cl
        sys.modules["bridge"].mgr = err_mock
        try:
            r = sc("execute_luau", {"code": "x=1"}, 30)
            assert r["ok"] is False
            assert r["kind"] == "timeout"
            assert "30s" in r["error"]
        finally:
            sys.modules["bridge"].mgr = mgr_backup

    def test_sc_returns_runtime_error(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        err_mock = MockMGR()

        def error_cl(name, args, timeout=30):
            raise RuntimeError("unknown tool 'bad_tool'")

        err_mock.cl = error_cl
        sys.modules["bridge"].mgr = err_mock
        try:
            r = sc("bad_tool", {}, 30)
            assert r["ok"] is False
            assert r["kind"] == "RuntimeError"
            assert "bad_tool" in r["error"]
        finally:
            sys.modules["bridge"].mgr = mgr_backup

    def test_sc_preserves_error_message(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        err_mock = MockMGR()

        def error_cl(name, args, timeout=30):
            raise ValueError("something broke")

        err_mock.cl = error_cl
        sys.modules["bridge"].mgr = err_mock
        try:
            r = sc("any_tool", {}, 30)
            assert r["ok"] is False
            assert "something broke" in r["error"]
        finally:
            sys.modules["bridge"].mgr = mgr_backup


class TestScSummarizationErrorHandling:
    def test_sc_handles_bad_json_gracefully(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        mock = MockMGR()
        mock.result = {"text": "not json " * 1000, "images": []}
        sys.modules["bridge"].mgr = mock
        try:
            r = sc("search_game_tree", {}, 30)
            assert r["ok"] is True  # should not crash
            assert r["text"] is not None
        finally:
            sys.modules["bridge"].mgr = mgr_backup

    def test_sc_handle_empty_result(self):
        from bridge import sc
        mgr_backup = sys.modules["bridge"].mgr
        mock = MockMGR()
        mock.result = {"text": "", "images": []}
        sys.modules["bridge"].mgr = mock
        try:
            r = sc("script_read", {"path": "x"}, 30)
            assert r["ok"] is True
            assert r["text"] == ""
        finally:
            sys.modules["bridge"].mgr = mgr_backup
