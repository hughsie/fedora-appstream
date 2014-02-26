/* -*- Mode: C; tab-width: 8; indent-tabs-mode: t; c-basic-offset: 8 -*-
 *
 * Copyright (C) 2014 Richard Hughes <richard@hughsie.com>
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

//gcc extract-gettext.c -o extract-gettext `pkg-config --cflags --libs glib-2.0`

#include <stdlib.h>
#include <glib.h>

typedef struct {
	guint32		 magic;
	guint32		 revision;
	guint32		 nstrings;
	guint32		 orig_tab_offset;
	guint32		 trans_tab_offset;
	guint32		 hash_tab_size;
	guint32		 hash_tab_offset;
	guint32		 n_sysdep_segments;
	guint32		 sysdep_segments_offset;
	guint32		 n_sysdep_strings;
	guint32		 orig_sysdep_tab_offset;
	guint32		 trans_sysdep_tab_offset;
} MoHeader;

typedef struct {
	gchar		*locale;
	guint		 nstrings;
	guint		 percentage;
} MoEntry;

typedef struct {
	guint		 max_nstrings;
	GList		*data;
} MoCtx;

/**
 * mo_entry_new:
 **/
static MoEntry *
mo_entry_new (void)
{
	MoEntry *entry;
	entry = g_slice_new0 (MoEntry);
	return entry;
}

/**
 * mo_entry_free:
 **/
static void
mo_entry_free (MoEntry *entry)
{
	g_free (entry->locale);
	g_slice_free (MoEntry, entry);
}

/**
 * mo_ctx_new:
 **/
static MoCtx *
mo_ctx_new (void)
{
	MoCtx *ctx;
	ctx = g_new0 (MoCtx, 1);
	return ctx;
}

/**
 * mo_ctx_free:
 **/
static void
mo_ctx_free (MoCtx *ctx)
{
	GList *l;
	for (l = ctx->data; l != NULL; l = l->next)
		mo_entry_free (l->data);
	g_free (ctx);
}

/**
 * mo_parse_file:
 **/
static gboolean
mo_parse_file (MoCtx *ctx,
	       const gchar *locale,
	       const gchar *filename,
	       GError **error)
{
	gboolean ret;
	gchar *data = NULL;
	MoEntry *entry;
	MoHeader *h;

	/* read data, although we only strictly need the header */
	ret = g_file_get_contents (filename, &data, NULL, error);
	if (!ret)
		goto out;

	h = (MoHeader *) data;
	entry = mo_entry_new ();
	entry->locale = g_strdup (locale);
	entry->nstrings = h->nstrings;
	if (entry->nstrings > ctx->max_nstrings)
		ctx->max_nstrings = entry->nstrings;
	ctx->data = g_list_prepend (ctx->data, entry);
out:
	g_free (data);
	return ret;
}

/**
 * mo_ctx_search_locale:
 **/
static gboolean
mo_ctx_search_locale (MoCtx *ctx,
		      const gchar *locale,
		      const gchar *messages_path,
		      GError **error)
{
	const gchar *filename;
	gboolean ret = TRUE;
	gchar *path;
	GDir *dir;

	dir = g_dir_open (messages_path, 0, error);
	if (dir == NULL) {
		ret = FALSE;
		goto out;
	}
	while ((filename = g_dir_read_name (dir)) != NULL) {
//		if (g_strcmp0 (filename, "gnome-software.mo") != 0)
//			continue;
		path = g_build_filename (messages_path, filename, NULL);
		if (g_file_test (path, G_FILE_TEST_EXISTS)) {
			ret = mo_parse_file (ctx, locale, path, error);
			if (!ret)
				goto out;
		}
		g_free (path);
	}
out:
	if (dir != NULL)
		g_dir_close (dir);
	return ret;
}

static gint
mo_entry_sort_cb (gconstpointer a, gconstpointer b)
{
	return g_strcmp0 (((MoEntry *) a)->locale, ((MoEntry *) b)->locale);
}

/**
 * mo_ctx_search_path:
 **/
static gboolean
mo_ctx_search_path (MoCtx *ctx, const gchar *prefix, GError **error)
{
	const gchar *filename;
	gboolean ret = TRUE;
	gchar *path;
	gchar *root = NULL;
	GDir *dir = NULL;
	GList *l;
	MoEntry *e;

	/* search for .mo files in the prefix */
	root = g_build_filename (prefix, "/usr/share/locale", NULL);
	dir = g_dir_open (root, 0, error);
	if (dir == NULL) {
		ret = FALSE;
		goto out;
	}
	while ((filename = g_dir_read_name (dir)) != NULL) {
		path = g_build_filename (root, filename, "LC_MESSAGES", NULL);
		if (g_file_test (path, G_FILE_TEST_EXISTS)) {
			ret = mo_ctx_search_locale (ctx, filename, path, error);
			if (!ret)
				goto out;
		}
		g_free (path);
	}

	/* calculate percentages */
	for (l = ctx->data; l != NULL; l = l->next) {
		e = l->data;
		e->percentage = MIN (e->nstrings * 100 / ctx->max_nstrings, 100);
	}

	/* sort */
	ctx->data = g_list_sort (ctx->data, mo_entry_sort_cb);
out:
	g_free (root);
	if (dir != NULL)
		g_dir_close (dir);
	return ret;
}

/**
 * main:
 **/
int
main (int argc, char *argv[])
{
	gboolean ret;
	gint retval = EXIT_SUCCESS;
	GError *error = NULL;
	GList *l;
	MoCtx *ctx = NULL;
	MoEntry *e;

	if (argc != 2) {
		g_print ("required, root\n");
		retval = EXIT_FAILURE;
		goto out;
	}

	/* search */
	ctx = mo_ctx_new ();
	ret = mo_ctx_search_path (ctx, argv[1], &error);
	if (!ret) {
		g_print ("FAILED: %s\n", error->message);
		g_error_free (error);
		retval = EXIT_FAILURE;
		goto out;
	}

	/* print results */
	for (l = ctx->data; l != NULL; l = l->next) {
		e = l->data;
		if (e->percentage < 25)
			continue;
		g_print ("%s\t%i\n", e->locale, e->percentage);
	}
out:
	if (ctx != NULL)
		mo_ctx_free (ctx);
	return retval;
}
