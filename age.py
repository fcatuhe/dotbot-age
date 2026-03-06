import os
import subprocess
from typing import Any

import dotbot


class Age(dotbot.Plugin):
    """
    Decrypt age-encrypted secrets and render templates into a private directory.
    Delegates to tools/decrypt for the actual work.
    """

    supports_dry_run = True

    _directive = "decrypt"

    def can_handle(self, directive: str) -> bool:
        return directive == self._directive

    def handle(self, directive: str, data: Any) -> bool:
        if directive != self._directive:
            msg = f"Age cannot handle directive {directive}"
            raise ValueError(msg)

        base = self._context.base_directory()
        decrypt_script = os.path.join(base, "dotbot-age", "tools", "decrypt")

        if not os.path.isfile(decrypt_script):
            self._log.error(f"Decrypt script not found: {decrypt_script}")
            return False

        if self._context.dry_run():
            self._log.action("Would decrypt secrets and render templates into private/")
            return True

        self._log.info("Decrypting secrets")

        try:
            result = subprocess.run(
                [decrypt_script],
                env={**os.environ, "DOTBOT_AGE_BASEDIR": base},
                capture_output=True,
                text=True,
            )
        except OSError as e:
            self._log.error(f"Failed to run decrypt: {e}")
            return False

        for line in result.stdout.strip().splitlines():
            self._log.info(line.strip())

        if result.returncode != 0:
            self._log.error(f"Decrypt failed: {result.stderr.strip()}")
            return False

        self._log.info("All secrets decrypted")
        return True
