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
 * Searches for appdata files
 * Outputs icons/tuxracer.png
 * Outputs appstream/tuxracer.xml
 * Outputs appstream/tuxracer-icons.tar
 * Deletes ./tmp and all contents

fedora-compose.py
---
 * Designed to be run on distro compose/mash
 * Joins all the appstream/*.xml files
 * Outputs appstream.xml.gz
 * Outputs appstream-icons.tar

fedora-download-cache.py f20 "fedora,fedora-updates"
---
 * Creates ./packages
 * Only used when making standalone metadata using existing repos
 * Searches existing files in packages/
 * Downloads any missing rpm files to packages/.rpm
 * Deletes any obsolete or removed packages

fedora-build-all.py
---
 * Only used when making standalone metadata using existing repos
 * Deletes ./appstream and all contents
 * Runs fedoraAppstream-build.py on all rpm files in packages/*

Using these tools
=================

If you manage a repository and want to generate AppStream metadata yourself
it's really quite easy if you follow these instructions, although building the
metadata can take a long time.

Lets assume you run a site called MegaRpms and you want to target Fedora 20.

First, checkout the latest version of fedora-appstream and create somewhere we
can store all the temporary files. You'll want to do this on a SSD if possible.

You'll need to have the following packages installed before starting:

 * python-pillow, optipng

You may also need the fonttools package installed if you are going to generate
metadata for any font packages.

$ mkdir megarpms
$ cd megarpms

Then create a project file with all the right settings for your repo.
Lets assume you have two seporate trees, 'megarpms' and 'meagarpms-updates'.

$ vim project.conf

[AppstreamProject]
DistroTag=f20
RepoIds=megarpms,megarpms-updates
DistroName=megarpms-20
ScreenshotMirrorUrl=http://www.megarpms.org/screenshots/

The screenshot mirror URL is required if you want to be able to host screenshots
for applications. If you don't want to (or can't afford the hosting costs) then
you can comment this out and no screenshots will be generated.

Then we can actually download the packages we need to extract. Ensure that both
megarpms and megarpms-updates are enabled in /etc/yum.conf.d/ and then start
downloading:

$ sudo ../fedora-download-cache.py

This requires root as it uses and updates the system metadata to avoid
duplicating the caches you've probably already got. After all the interesting
packages are downloaded you can do:

$ ../fedora-build-all.py

Now, go and make a cup of tea and wait patiently if you have a lot of packages
to process. After this is complete you can do:

$ ../fedora-compose.py

This spits out megarpms-20.xml.gz and megarpms-20-icons.tar.gz -- and you now
have two choices what to do with these files. You can either upload them with
the rest of the metadata you ship (e.g. in the same directory as repomd.xml
and primary.sqlite.bz2) which will work with Fedora 21 and higher.

For Fedora 20, you have to actually install these files, so you can do something
like this in the megarpms-release.spec file:

Source1:   http://www.megarpms.org/temp/megarpms-20.xml.gz
Source2:   http://www.megarpms.org/temp/megarpms-20-icons.tar.gz

mkdir -p %{buildroot}%{_datadir}/app-info/xmls
cp %{SOURCE1} %{buildroot}%{_datadir}/app-info/xmls
mkdir -p %{buildroot}%{_datadir}/app-info/icons/megarpms-20
tar xvzf %{SOURCE2}
cd -

This ensures that gnome-software can access both data files when starting up.
If you have any other questions, concerns or patches, please get in touch.
