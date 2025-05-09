import os
from gettext import gettext as _, pgettext as C_

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GObject

from gdms import APP_NAME, APP_ID, DEBUG
from gdms.utils import BackgroundTask, GProperty, GSettings
from gdms.cmd import Command
from gdms.gresource import UbuntuGdmGresourceFile, BackgroundImageNotFoundError
from gdms import settings

from . import pages
from .sidebar import Sidebar


class TaskCounter(GObject.Object):
    '''A GObject that keeps a count of background tasks and updates widgets accordingly'''

    __gtype_name__ = 'TaskCounter'

    count = GProperty(int, default=0)
    spinner = GProperty(Gtk.Spinner)

    def __init__ (self, **props):
        super().__init__(**props)

        self.widgets = []

        self.connect('notify::count', self.on_count_change)


    @staticmethod
    def on_count_change (self, prop):
        if self.count > 0:
            for widget in self.widgets:
                widget.set_sensitive(False)
            self.spinner.start()
        else:
            for widget in self.widgets:
                widget.set_sensitive(True)
            self.spinner.stop()

    def register (self, widget):
        self.widgets.append(widget)

    def inc (self):
        self.count += 1

    def dec (self):
        self.count -= 1


class GdmSettingsWindow (Adw.ApplicationWindow):
    __gtype_name__ = 'GdmSettingsWindow'

    def __init__ (self, application, **props):
        super().__init__(**props)

        if DEBUG:
            self.add_css_class('devel')

        self.application = application
        self.set_application(application)

        self.props.title = APP_NAME
        self.props.width_request = 360
        self.props.height_request = 360

        self.builder = Gtk.Builder.new_from_resource('/app/ui/main-window.ui')

        self.stack = self.builder.get_object('stack')
        self.sidebar = self.builder.get_object('sidebar')
        self.spinner = self.builder.get_object('spinner')
        self.split_view = self.builder.get_object('split_view')
        self.apply_button = self.builder.get_object('apply_button')
        self.section_label = self.builder.get_object('section_label')
        self.toast_overlay = self.builder.get_object('toast_overlay')

        self.set_content(self.toast_overlay)

        self.task_counter = TaskCounter(spinner=self.spinner)

        self.task_counter.register(self.apply_button)
        self.apply_button.connect('clicked', self.on_apply)
        self.apply_task = BackgroundTask(settings.apply, self.on_apply_finished)

        self.sidebar.connect('activate', self.on_sidebar_activate, self.split_view)
        self.stack.connect('notify::visible-child', self.on_section_changed)

        condition = Adw.BreakpointCondition.parse('max-width: 500sp')
        breakpoint = Adw.Breakpoint.new(condition);
        breakpoint.add_setter(self.split_view, 'collapsed', True)
        self.add_breakpoint(breakpoint);

        self.add_pages()
        self.bind_to_gsettings()

    def on_sidebar_activate (self, sidebar, split_view):
        split_view.props.show_content = True

    def on_section_changed (self, stack, prop):
        current_page = stack.get_page(stack.props.visible_child)
        self.section_label.set_label(current_page.get_title())

    def add_pages (self):

        def add_page(name, title, content):
            page = self.stack.add_titled(content, name, title)
            page.props.icon_name = name + '-symbolic'

        add_page('appearance', _('Appearance'),       pages.AppearancePageContent(self))
        add_page('fonts',      _('Fonts'),            pages.FontsPageContent(self))
        add_page('top_bar',    _('Top Bar'),          pages.TopBarPageContent(self))
        add_page('sound',      _('Sound'),            pages.SoundPageContent(self))
        add_page('pointing',   _('Mouse & Touchpad'), pages.PointingPageContent(self))
        add_page('display',    _('Display'),          pages.DisplayPageContent(self))
        add_page('misc',       _('Login Screen'),     pages.LoginScreenPageContent(self))
        add_page('power',      _('Power'),            pages.PowerPageContent(self))
        add_page('tools',      _('Tools'),            pages.ToolsPageContent(self))

    def bind_to_gsettings (self):
        self.settings = GSettings(APP_ID + '.window-state')

        self.settings.bind('width', self, 'default-width')
        self.settings.bind('height', self, 'default-height')
        self.settings.bind('last-visited-page', self.stack, 'visible-child-name')

    def on_apply (self, button):
        self.task_counter.inc()
        self.apply_task.start()

    def on_apply_finished(self):
        self.task_counter.dec()

        try:
            if self.apply_task.finish():
                message = _('Settings applied successfully')
                if os.environ.get('XDG_CURRENT_DESKTOP') == 'GNOME' and not UbuntuGdmGresourceFile:
                    self.show_logout_dialog()
            else:
                message = _('Failed to apply settings')
            toast = Adw.Toast(timeout=2, priority='high', title=message)

        except BackgroundImageNotFoundError:
            message = _("Didn't apply. Chosen background image does not exist anymore. Please! choose again.")
            toast = Adw.Toast(timeout=4, priority='high', title=message)

        except settings.LogoImageNotFoundError:
            message = _("Didn't apply. Chosen logo image does not exist anymore. Please! choose again.")
            toast = Adw.Toast(timeout=4, priority='high', title=message)

        self.toast_overlay.add_toast(toast)

    def show_logout_dialog (self):
        message = _('The system may start to look weird/buggy until you re-login or reboot.')

        dialog = Adw.MessageDialog(
                    body = message,
                   modal = True,
                 heading = _('Log Out?'),
           transient_for = self,
         body_use_markup = True,
        )

        dialog.add_response('cancel', _('Cancel'))
        dialog.add_response('log-out', _('Log Out'))
        dialog.set_response_appearance('log-out', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect('response', self.on_logout_dialog_response)
        dialog.present()

    def on_logout_dialog_response (self, dialog, response):
        if response == 'log-out':
            Command('gnome-session-quit --no-prompt').run()
