import re
import logging
from gettext import gettext as _, pgettext as C_

import gi
from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GObject

from . import info
from .lib import Property


mazhar_hussain = C_("Name of Developer", "Mazhar Hussain") + " <realmazharhussain@gmail.com>"
thales_binda   = C_("Name of Artist",    "Thales Bindá") +   " <thales.i.o.b@gmail.com>"


try:
    gi.require_version('AppStreamGlib', '1.0')
    from gi.repository import AppStreamGlib as ASG
except (ValueError, ImportError):
    ASG = None

class ReleaseNotesFetcher(GObject.Object):
    __gtype_name__ = 'ReleaseNotesFetcher'
    _instance = None

    notes = Property(str, default="")
    version = Property(str, default="")

    def __new__(cls):
        if not cls._instance:
            return super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not type(self)._instance:
            super().__init__()
            type(self)._instance = self
            self.store = None

        if self.store:
            return

        if not ASG:
            logging.warning('AppStreamGlib typelib not installed! Cannot get release information.')
            return

        self.store = ASG.Store()
        self.store.load_async(flags=ASG.StoreLoadFlags.APPDATA, callback=self.on_store_load)

    def on_store_load(self, store, result, user_data=None):
        if not store.load_finish(result):
            return

        app_info = store.get_app_by_id(info.application_id)
        if not app_info:
            return

        releases = app_info.get_releases()
        if not releases:
            return

        current_major = re.findall(r'[0-9]+', info.version)[0]
        current_releases = (r for r in releases if r.get_version().startswith(current_major))
        current_releases_with_desc = [r for r in current_releases if r.get_description()]

        if not current_releases_with_desc:
            return

        def is_stable(release):
            return release.get_kind() is not ASG.ReleaseKind.DEVELOPMENT

        relevant_releases = current_releases_with_desc
        if is_stable(current_releases_with_desc[0]):
            relevant_releases = [r for r in current_releases_with_desc if is_stable(r)]

        notes = ""
        if len(relevant_releases) == 1:
            self.version = relevant_releases[0].get_version()
            notes = relevant_releases[0].get_description()
        else:
            self.version = current_major
            for release in relevant_releases:
                notes += "<p>##### %s #####</p>" % release.get_version()
                notes += release.get_description()

        self.notes = notes.replace('&gt;', '>').replace('&lt;', '<')


def about_window(win):
    abt = Adw.AboutWindow(
        transient_for = win,
        modal         = True,
        application_name = info.application_name,
        application_icon = info.application_id,
        license_type     = Gtk.License.AGPL_3_0,
        version          = info.version,
        developer_name   = C_("Name of Developer", "Mazhar Hussain"),
        copyright = _("Copyright 2021-2023 Mazhar Hussain"),
        website   = "https://gdm-settings.github.io",
        developers  = [mazhar_hussain],
        designers   = [mazhar_hussain],
        documenters = [mazhar_hussain],
        artists     = [thales_binda],

        support_url = "https://github.com/gdm-settings/gdm-settings/discussions/categories/q-a",
        issue_url   = "https://github.com/gdm-settings/gdm-settings/issues/new/choose",

        # Translators: Do not translate this string. Put your info here in the form
        # 'name <email>' including < and > but not quotes.
        translator_credits = _("translator-credits"),
        )

    fetcher = ReleaseNotesFetcher()
    flags = GObject.BindingFlags.SYNC_CREATE;
    fetcher.bind_property("notes", abt, "release-notes", flags)
    fetcher.bind_property("version", abt, "release-notes-version", flags)

    return abt
