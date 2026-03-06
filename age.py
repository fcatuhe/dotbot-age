import os
import shutil
import subprocess
from typing import Any

import dotbot


class Age(dotbot.Plugin):
    """
    Decrypt age-encrypted secrets and render templates into a private directory.

    Convention (all paths relative to base directory):
      - encrypted/age.key          identity (private key)
      - encrypted/secrets.env.age  encrypted KEY=VALUE vars
      - encrypted/*/               template files with {{PLACEHOLDERS}}
      - private/                   rendered output

    All conventions can be overridden via the decrypt directive config.
    """

    supports_dry_run = True

    _directive = "decrypt"

    # Defaults (convention)
    _default_key = "encrypted/age.key"
    _default_vars = "encrypted/secrets.env.age"
    _default_encrypted = "encrypted"
    _default_private = "private"

    def can_handle(self, directive: str) -> bool:
        return directive == self._directive

    def handle(self, directive: str, data: Any) -> bool:
        if directive != self._directive:
            msg = f"Age cannot handle directive {directive}"
            raise ValueError(msg)
        return self._process(data)

    def _process(self, data: Any) -> bool:
        base = self._context.base_directory()

        # Read config or use conventions
        if not isinstance(data, dict):
            data = {}

        key = os.path.join(base, data.get("key", self._default_key))
        vars_file = os.path.join(base, data.get("vars", self._default_vars))
        encrypted_dir = os.path.join(base, data.get("encrypted", self._default_encrypted))
        private_dir = os.path.join(base, data.get("private", self._default_private))

        # Validate
        if not os.path.isfile(key):
            self._log.error(f"Age identity not found: {key}")
            return False

        if not os.path.isfile(vars_file):
            self._log.error(f"Encrypted vars not found: {vars_file}")
            return False

        if not os.path.isdir(encrypted_dir):
            self._log.error(f"Encrypted directory not found: {encrypted_dir}")
            return False

        # Check age is installed
        if not shutil.which("age"):
            self._log.error("age is not installed (https://github.com/FiloSottile/age)")
            return False

        # Decrypt vars
        self._log.info("Decrypting secrets")
        if self._context.dry_run():
            self._log.action(f"Would decrypt {vars_file} and render templates to {private_dir}")
            return True

        try:
            result = subprocess.run(
                ["age", "-d", "-i", key, vars_file],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self._log.error(f"Failed to decrypt {vars_file}: {e.stderr.strip()}")
            return False

        # Parse KEY=VALUE pairs
        secrets = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            secrets[k] = v

        # Find and render templates
        success = True
        skip_names = {"age.key", "secrets.env.age"}
        skip_extensions = {".age"}

        for dirpath, _dirnames, filenames in os.walk(encrypted_dir):
            # Only process files in subdirectories of encrypted/
            if dirpath == encrypted_dir:
                continue

            for filename in filenames:
                if filename in skip_names:
                    continue
                if any(filename.endswith(ext) for ext in skip_extensions):
                    continue

                src = os.path.join(dirpath, filename)
                relative = os.path.relpath(src, encrypted_dir)
                dest = os.path.join(private_dir, relative)

                try:
                    with open(src) as f:
                        content = f.read()
                except OSError as e:
                    self._log.warning(f"Failed to read {src}: {e}")
                    success = False
                    continue

                # Substitute {{KEY}} placeholders
                for k, v in secrets.items():
                    content = content.replace("{{" + k + "}}", v)

                # Check for unresolved placeholders
                import re

                unresolved = re.findall(r"\{\{(\w+)\}\}", content)
                if unresolved:
                    self._log.warning(f"Unresolved placeholders in {relative}: {', '.join(unresolved)}")

                # Write only if content changed
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                needs_write = True
                if os.path.isfile(dest):
                    with open(dest) as f:
                        if f.read() == content:
                            needs_write = False
                            self._log.info(f"Unchanged {relative}")

                if needs_write:
                    with open(dest, "w") as f:
                        f.write(content)
                    self._log.action(f"Rendered {relative}")

        # Set permissions: 700 dirs, 600 files
        for dirpath, dirnames, filenames in os.walk(private_dir):
            os.chmod(dirpath, 0o700)
            for filename in filenames:
                os.chmod(os.path.join(dirpath, filename), 0o600)

        self._log.info("All secrets decrypted")
        return success
