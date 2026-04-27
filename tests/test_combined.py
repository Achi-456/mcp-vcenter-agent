"""Light tests for merged tool registry and govc policy."""
import unittest

from app.tools.combined import build_combined_tools, execute_combined
from app.tools.integrations_govc import govc_command


class TestCombined(unittest.TestCase):
    def test_combined_includes_govc_and_web_search(self):
        tools, dispatch = build_combined_tools()
        names = {t["name"] for t in tools}
        self.assertIn("govc_command", names)
        self.assertIn("web_search", names)
        self.assertIn("connect_vcenter", names)
        self.assertIn("govc_command", dispatch)
        self.assertIn("web_search", dispatch)

    def test_govc_blocks_destroy(self):
        r = govc_command("vm.destroy /path")
        self.assertIn("error", r)

    def test_execute_unknown_tool(self):
        _, d = build_combined_tools()
        r = execute_combined("not_a_real_tool_xyz", {}, d)
        self.assertIn("error", r)


if __name__ == "__main__":
    unittest.main()
