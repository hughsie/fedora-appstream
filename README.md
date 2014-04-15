fedora-appstream
================

fedora-download-cache.py f20 "fedora,fedora-updates"
---
 * Creates ./packages
 * Only used when making standalone metadata using existing repos
 * Searches existing files in packages/
 * Downloads any missing rpm files to packages/.rpm
 * Deletes any obsolete or removed packages
