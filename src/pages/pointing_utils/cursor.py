from gettext import pgettext as C_

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GObject

from ...utils import resource_path
from ...lib import Property


@Gtk.Template(resource_path=resource_path('ui/pointing-page/cursor-size-button.ui'))
class CursorSizeButton (Gtk.ToggleButton):
    __gtype_name__ = 'CursorSizeButton'

    cursor_size = Property(int, default=24, construct_only=True)
    size_name = Property(str)


@Gtk.Template(resource_path=resource_path('ui/pointing-page/cursor-size-selector.ui'))
class CursorSizeSelector (Gtk.ListBoxRow, Gtk.Buildable):
    __gtype_name__ = 'CursorSizeSelector'
    box = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self._item_dict = {}
        self._first_item = None
        self._selected_size = 0
        self._selected_name = ''

    @Property(int)
    def selected_size(self):
        return self._selected_size

    @selected_size.setter
    def selected_size(self, value):
        if self._selected_size == value:
            return

        if value not in self._item_dict:
            return

        self._selected_size = value
        btn = self._item_dict[value]
        btn.set_active(True)

        self._selected_name = btn.size_name
        self.notify('selected-name')

    @Property(str, writable=False)
    def selected_name(self):
        return self._selected_name

    def do_add_child(self, builder, child, _type):
        if not isinstance(child, CursorSizeButton):
            raise TypeError('Child is a ' + type(child) + '. Should be a CursorSizeButton instead')

        cursor_size = child.cursor_size
        if cursor_size in self._item_dict:
            raise ValueError('A CursorSizeButton with cursor-size of ' + cursor_size
                             + ' has already been added')

        self.box.append(child)
        child.connect('toggled', self.selection_changed_cb)
        self._item_dict[cursor_size] = child

        if self._first_item:
            child.set_group(self._first_item)
        else:
            self._first_item = child
            child.set_active(True)

    def selection_changed_cb(self, child):
        if not child.get_active() or child.cursor_size == self.selected_size:
            return

        self.selected_size = child.cursor_size
