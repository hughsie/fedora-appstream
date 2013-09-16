fedora-appstream
================

AppStream tools for Fedora

build.py pkgs/tr-1.0-1.fc20.rpm
---
 * Creates ./appstream
 * Creates ./icons
 * Creates ./tmp
 * Designed to be run after the package has been built on koji
 * Explodes the rpm file into ./tmp
 * Searches for desktop files
 * *TODO: searches for appdata files*
 * Outputs icons/tuxracer.png
 * Outputs appstream/tuxracer.xml
 * Outputs appstream/tuxracer-icons.tar
 * Deletes ./tmp and all contents

fedora-compose.py
---
 * Designed to be run on distro compose/mash
 * Joins all the appstream/*.xml files
 * Outputs appstream.xml.gz
 * TODO: outputs appstream-icons.tar

fedora-download-cache.py f20 "fedora,fedora-updates"
---
 * Creates ./packages
 * Only used when making standalone metadata using existing repos
 * Searches existing files in packages/
 * Downloads any missing rpm files to packages/.rpm
 * *TODO: needs to also download other things from the srpm*
 * Deletes any obsolete or removed packages

fedora-build-all.py
---
 * Only used when making standalone metadata using existing repos
 * Deletes ./appstream and all contents
 * Runs fedoraAppstream-build.py on all rpm files in packages/*
