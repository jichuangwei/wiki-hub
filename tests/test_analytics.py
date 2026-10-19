import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_site import SITE, build


class AnalyticsBuildTests(unittest.TestCase):
    def test_tracking_covers_content_pages_and_excludes_redirects(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build(output, " G-TEST123456 ")
            for page in output.rglob("*.html"):
                content = page.read_text(encoding="utf-8")
                with self.subTest(page=page.relative_to(output)):
                    if 'class="site-header"' not in content:
                        self.assertNotIn("analytics.js", content)
                        self.assertNotIn("G-TEST123456", content)
                        continue
                    self.assertEqual(content.count('data-measurement-id="G-TEST123456"'), 1)
                    source = re.search(r'src="([^"]+analytics\.js)\?v=', content).group(1)
                    self.assertEqual((page.parent / source).resolve(), (output / "assets/analytics.js").resolve())
                    self.assertNotIn("{{", content)

    def test_unconfigured_build_does_not_load_analytics(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build(output)
            for page in output.rglob("*.html"):
                content = page.read_text(encoding="utf-8")
                self.assertNotIn("analytics.js", content)
                self.assertNotIn("SITE_ANALYTICS", content)

    def test_invalid_id_is_rejected_before_existing_output_is_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            sentinel = output / "keep.txt"
            sentinel.write_text("existing build", encoding="utf-8")
            for measurement_id in ('G-X\"><script>', 'UA-123-1', 'G-ABC?x=1'):
                with self.subTest(measurement_id=measurement_id), self.assertRaises(ValueError):
                    build(output, measurement_id)
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "existing build")


@unittest.skipUnless(shutil.which("node"), "Node.js is needed to verify browser analytics initialization")
class AnalyticsRuntimeTests(unittest.TestCase):
    def test_initialization_local_preview_and_duplicate_loading(self):
        harness = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
function run(hostname, protocol = 'https:', measurementId = 'G-TEST123456') {
  const scripts = [];
  const context = vm.createContext({
    window: { location: { hostname, protocol } },
    document: {
      currentScript: { dataset: { measurementId } },
      createElement: () => ({}),
      head: { append: script => scripts.push(script) },
    },
  });
  vm.runInContext(source, context);
  vm.runInContext(source, context);
  return { scripts, commands: (context.window.dataLayer || []).map(args => Array.from(args)) };
}
console.log(JSON.stringify({
  public: run('jichuangwei.github.io'),
  custom: run('wiki.example.org'),
  excluded: ['localhost', 'preview.localhost', '127.0.0.1', '127.0.0.2', '[::1]', '::1']
    .map(host => run(host)),
  file: run('', 'file:'),
  invalid: run('jichuangwei.github.io', 'https:', 'G-X?foo=bar'),
}));
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", harness, str(SITE / "assets/analytics.js")],
            check=True, capture_output=True, text=True,
        )
        data = json.loads(result.stdout)
        for name in ("public", "custom"):
            with self.subTest(name=name):
                self.assertEqual(data[name]["scripts"], [{
                    "async": True,
                    "src": "https://www.googletagmanager.com/gtag/js?id=G-TEST123456",
                }])
                commands = data[name]["commands"]
                self.assertEqual([command[0] for command in commands], ["js", "config"])
                self.assertEqual(commands[1][1], "G-TEST123456")
                self.assertFalse(commands[1][2]["allow_google_signals"])
                self.assertFalse(commands[1][2]["allow_ad_personalization_signals"])
        for result in data["excluded"] + [data["file"], data["invalid"]]:
            self.assertEqual(result, {"scripts": [], "commands": []})
