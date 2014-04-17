# Copyright 2014 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""The main tabbed browser widget."""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QObject
from PyQt5.QtGui import QClipboard
from PyQt5.QtPrintSupport import QPrintPreviewDialog

import qutebrowser.utils.url as urlutils
import qutebrowser.commands.utils as cmdutils


class CurCommandDispatcher(QObject):

    """Command dispatcher for TabbedBrowser.

    Contains all commands which are related to the current tab.

    We can't simply add these commands to BrowserTab directly and use
    currentWidget() for TabbedBrowser.cur because at the time
    cmdutils.register() decorators are run, currentWidget() will return None.

    Attributes:
        tabs: The TabbedBrowser object.

    Signals:
        temp_message: Connected to TabbedBrowser signal.
    """

    # FIXME maybe subclassing would be more clean?

    temp_message = pyqtSignal(str)

    def __init__(self, parent):
        """Constructor.

        Uses setattr to get some methods from parent.

        Args:
            parent: The TabbedBrowser for this dispatcher.
        """
        super().__init__(parent)
        self.tabs = parent

    def _scroll_percent(self, perc=None, count=None, orientation=None):
        """Inner logic for scroll_percent_(x|y).

        Args:
            perc: How many percent to scroll, or None
            count: How many percent to scroll, or None
            orientation: Qt.Horizontal or Qt.Vertical
        """
        if perc is None and count is None:
            perc = 100
        elif perc is None:
            perc = int(count)
        else:
            perc = float(perc)
        frame = self.tabs.currentWidget().page_.mainFrame()
        m = frame.scrollBarMaximum(orientation)
        if m == 0:
            return
        frame.setScrollBarValue(orientation, int(m * perc / 100))

    @cmdutils.register(instance='mainwindow.tabs.cur', name='open', maxsplit=0)
    def openurl(self, url, count=None):
        """Open an url in the current/[count]th tab.

        Command handler for :open.

        Args:
            url: The URL to open.
            count: The tab index to open the URL in, or None.
        """
        tab = self.tabs.cntwidget(count)
        if tab is None:
            if count is None:
                # We want to open an URL in the current tab, but none exists
                # yet.
                self.tabs.tabopen(url)
            else:
                # Explicit count with a tab that doesn't exist.
                return
        else:
            tab.openurl(url)

    @cmdutils.register(instance='mainwindow.tabs.cur', name='reload')
    def reloadpage(self, count=None):
        """Reload the current/[count]th tab.

        Command handler for :reload.

        Args:
            count: The tab index to reload, or None.
        """
        tab = self.tabs.cntwidget(count)
        if tab is not None:
            tab.reload()

    @cmdutils.register(instance='mainwindow.tabs.cur')
    def stop(self, count=None):
        """Stop loading in the current/[count]th tab.

        Command handler for :stop.

        Args:
            count: The tab index to stop, or None.
        """
        tab = self.tabs.cntwidget(count)
        if tab is not None:
            tab.stop()

    @cmdutils.register(instance='mainwindow.tabs.cur', name='print')
    def printpage(self, count=None):
        """Print the current/[count]th tab.

        Command handler for :print.

        Args:
            count: The tab index to print, or None.
        """
        # FIXME that does not what I expect
        tab = self.tabs.cntwidget(count)
        if tab is not None:
            preview = QPrintPreviewDialog(self)
            preview.paintRequested.connect(tab.print)
            preview.exec_()

    @cmdutils.register(instance='mainwindow.tabs.cur')
    def back(self, count=1):
        """Go back in the history of the current tab.

        Command handler for :back.

        Args:
            count: How many pages to go back.
        """
        # FIXME display warning if beginning of history
        for _ in range(count):
            self.tabs.currentWidget().back()

    @cmdutils.register(instance='mainwindow.tabs.cur')
    def forward(self, count=1):
        """Go forward in the history of the current tab.

        Command handler for :forward.

        Args:
            count: How many pages to go forward.
        """
        # FIXME display warning if end of history
        for _ in range(count):
            self.tabs.currentWidget().forward()

    @pyqtSlot(str, int)
    def search(self, text, flags):
        """Search for text in the current page.

        Args:
            text: The text to search for.
            flags: The QWebPage::FindFlags.
        """
        self.tabs.currentWidget().findText(text, flags)

    @cmdutils.register(instance='mainwindow.tabs.cur', hide=True)
    def scroll(self, dx, dy, count=1):
        """Scroll the current tab by count * dx/dy.

        Command handler for :scroll.

        Args:
            dx: How much to scroll in x-direction.
            dy: How much to scroll in x-direction.
            count: multiplier
        """
        dx = int(count) * float(dx)
        dy = int(count) * float(dy)
        self.tabs.currentWidget().page_.mainFrame().scroll(dx, dy)

    @cmdutils.register(instance='mainwindow.tabs.cur', name='scroll_perc_x',
                       hide=True)
    def scroll_percent_x(self, perc=None, count=None):
        """Scroll the current tab to a specific percent of the page (horiz).

        Command handler for :scroll_perc_x.

        Args:
            perc: Percentage to scroll.
            count: Percentage to scroll.
        """
        self._scroll_percent(perc, count, Qt.Horizontal)

    @cmdutils.register(instance='mainwindow.tabs.cur', name='scroll_perc_y',
                       hide=True)
    def scroll_percent_y(self, perc=None, count=None):
        """Scroll the current tab to a specific percent of the page (vert).

        Command handler for :scroll_perc_y

        Args:
            perc: Percentage to scroll.
            count: Percentage to scroll.
        """
        self._scroll_percent(perc, count, Qt.Vertical)

    @cmdutils.register(instance='mainwindow.tabs.cur', hide=True)
    def scroll_page(self, mx, my, count=1):
        """Scroll the frame page-wise.

        Args:
            mx: How many pages to scroll to the right.
            my: How many pages to scroll down.
            count: multiplier
        """
        # FIXME this might not work with HTML frames
        page = self.tabs.currentWidget().page_
        size = page.viewportSize()
        page.mainFrame().scroll(int(count) * float(mx) * size.width(),
                                int(count) * float(my) * size.height())

    @cmdutils.register(instance='mainwindow.tabs.cur')
    def yank(self, sel=False):
        """Yank the current url to the clipboard or primary selection.

        Command handler for :yank.

        Args:
            sel: True to use primary selection, False to use clipboard

        Emit:
            temp_message to display a temporary message.
        """
        clip = QApplication.clipboard()
        url = urlutils.urlstring(self.tabs.currentWidget().url())
        mode = QClipboard.Selection if sel else QClipboard.Clipboard
        clip.setText(url, mode)
        self.temp_message.emit('URL yanked to {}'.format(
            'primary selection' if sel else 'clipboard'))

    @cmdutils.register(instance='mainwindow.tabs.cur', name='yanktitle')
    def yank_title(self, sel=False):
        """Yank the current title to the clipboard or primary selection.

        Command handler for :yanktitle.

        Args:
            sel: True to use primary selection, False to use clipboard

        Emit:
            temp_message to display a temporary message.
        """
        clip = QApplication.clipboard()
        title = self.tabs.tabText(self.tabs.currentIndex())
        mode = QClipboard.Selection if sel else QClipboard.Clipboard
        clip.setText(title, mode)
        self.temp_message.emit('Title yanked to {}'.format(
            'primary selection' if sel else 'clipboard'))

    @cmdutils.register(instance='mainwindow.tabs.cur', name='zoomin')
    def zoom_in(self, count=1):
        """Zoom in in the current tab.

        Args:
            count: How many steps to take.
        """
        tab = self.tabs.currentWidget()
        tab.zoom(count)

    @cmdutils.register(instance='mainwindow.tabs.cur', name='zoomout')
    def zoom_out(self, count=1):
        """Zoom out in the current tab.

        Args:
            count: How many steps to take.
        """
        tab = self.tabs.currentWidget()
        tab.zoom(-count)