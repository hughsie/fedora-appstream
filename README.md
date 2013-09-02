fedora-appstream
================

AppStream tools for Fedora

Commands:

fedoraAppstreamBuildPkg.py packages/tuxracer-1.0-1.fc20.rpm
	creates ./appstream
	creates ./icons
	creates ./tmp
	designed to be run after the package has been built on koji
	explodes the rpm file into ./tmp
	searches for desktop files
	TODO: searches for appdata files
	outputs icons/tuxracer.png
	outputs appstream/tuxracer.xml
	outputs appstream/tuxracer-icons.tar
	deletes ./tmp and all contents

fedoraAppstreamCompose.py
	designed to be run on distro compose/mash
	joins all the appstream/*.xml files
	outputs appstream.xml.gz
	TODO: outputs appstream-icons.tar

fedoraAppstreamCache.py --repo=f20
	creates ./packages
	only used when making standalone metadata using existing repos
	TODO: downloads all the rpm files to packages/*.rpm

fedoraAppstreamBuildAll.py
	only used when making standalone metadata using existing repos
	deletes ./appstream and all contents
	runs fedoraAppstream-build.py on all rpm files in packages/*
