/* -*- Mode: C; tab-width: 8; indent-tabs-mode: t; c-basic-offset: 8 -*-
 *
 * Copyright (C) 2010 Richard Hughes <richard@hughsie.com>
 *
 * Licensed under the GNU General Public License Version 2
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 */

//gcc extract-package.c -o extract-package `pkg-config --cflags --libs libarchive`

#include <stdlib.h>
#include <limits.h>
#include <archive.h>
#include <archive_entry.h>

#define BLOCK_SIZE	(1024 * 4 * 10) /* bytes */

int
main (int argc, char *argv[])
{
	int rc = 0;
	struct archive *arch = NULL;
	struct archive_entry *entry;
	int r;
	int retval;
	char *retcwd;
	char buf[PATH_MAX];

	/* check */
	if (argc != 3) {
		fprintf (stderr, "arguments incorrect\n");
		goto out;
	}

	/* save the PWD as we chdir to extract */
	retcwd = getcwd (buf, PATH_MAX);
	if (retcwd == NULL) {
		rc = 1;
		fprintf (stderr, "failed to get cwd\n");
		goto out;
	}

	/* read anything */
	arch = archive_read_new ();
	archive_read_support_format_all (arch);
	archive_read_support_compression_all (arch);

	/* open the tar file */
	r = archive_read_open_file (arch, argv[1], BLOCK_SIZE);
	if (r) {
		rc = 1;
		fprintf (stderr, "cannot open: %s\n", archive_error_string (arch));
		goto out;
	}

	/* switch to our destination directory */
	retval = chdir (argv[2]);
	if (retval != 0) {
		rc = 1;
		fprintf (stderr, "failed chdir to %s\n", argv[2]);
		goto out;
	}

	/* decompress each file */
	for (;;) {
		r = archive_read_next_header (arch, &entry);
		if (r == ARCHIVE_EOF)
			break;
		if (r != ARCHIVE_OK) {
			rc = 1;
			fprintf (stderr, "cannot read header: %s\n", archive_error_string (arch));
			goto out;
		}
		r = archive_read_extract (arch, entry, 0);
		if (r != ARCHIVE_OK) {
			rc = 1;
			fprintf (stderr, "cannot extract: %s\n", archive_error_string (arch));
			goto out;
		}
	}

out:
	/* close the archive */
	if (arch != NULL) {
		archive_read_close (arch);
		archive_read_finish (arch);
	}

	/* switch back to PWD */
	retval = chdir (buf);
	if (retval != 0) {
		rc = 1;
		fprintf (stderr, "cannot chdir back!\n");
	}

	return rc;
}
