fedora-appstream
================

AppStream tools for Fedora

fedoraAppstreamBuildPkg.py pkgs/tr-1.0-1.fc20.rpm
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

fedoraAppstreamCompose.py
---
 * Designed to be run on distro compose/mash
 * Joins all the appstream/*.xml files
 * Outputs appstream.xml.gz
 * TODO: outputs appstream-icons.tar

fedoraAppstreamCache.py f20
---
 * Creates ./packages
 * Only used when making standalone metadata using existing repos
 * *TODO: downloads all the rpm files to packages/.rpm*

fedoraAppstreamBuildAll.py
---
 * Only used when making standalone metadata using existing repos
 * Deletes ./appstream and all contents
 * Runs fedoraAppstream-build.py on all rpm files in packages/*
