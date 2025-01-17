import os
import sys
import platform as arch
import subprocess
import requests

import proxy
import bookmark
from webkit import *
from confvar import *
import extension
import lynxutils as lxu

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import PyQt5.QtWebEngineWidgets
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtPrintSupport import *
from PyQt5.QtWebEngineCore import *
from PyQt5.QtWebChannel import QWebChannel

default_url_open = None 
downloading_item = False
download_directory = DOWNLOAD_PATH
progress_color_loading = grab_stylesheet_value("QLineEdit", "background-color")
webkit_background_color = grab_stylesheet_value("Background", "background-color")

def open_folder(path):
    if arch.system() == "Windows":
        os.startfile(path)
    elif arch.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])

def open_url_arg(url):
    global default_url_open
    default_url_open = url

interceptor = RequestInterceptor()
webchannel = WebChannel()

def launch_stealth(window):
    exec_file = sys.argv[0]
    window.close()
    if ".py" in exec_file:
        subprocess.run([sys.executable, exec_file, "-s"])
    else:
        subprocess.run([exec_file, "-s"])

if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    PyQt5.QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    PyQt5.QtWidgets.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        global BROWSER_HOMEPAGE
        
        self.first_opened = False
        self.last_closed_tab = None
        self.tab_indexes = []

        if BROWSER_PROXY:
            proxy.setProxy(BROWSER_PROXY)

        self.settings = QWebEngineSettings.defaultSettings()
        self.settings.setAttribute(QWebEngineSettings.JavascriptEnabled, WEBKIT_JAVASCRIPT_ENABLED)
        self.settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, WEBKIT_FULLSCREEN_ENABLED)
        self.settings.setAttribute(QWebEngineSettings.WebGLEnabled, WEBKIT_WEBGL_ENABLED)
        self.settings.setAttribute(QWebEngineSettings.PluginsEnabled, WEBKIT_PLUGINS_ENABLED)
        self.settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, 1)
        self.settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, WEBKIT_JAVASCRIPT_POPUPS_ENABLED)
        QWebEngineProfile.defaultProfile().setRequestInterceptor(interceptor)

        if BROWSER_STORE_VISITED_LINKS != True:
            QWebEngineProfile.defaultProfile().clearAllVisitedLinks()

        if BROWSER_STORAGE:
            QWebEngineProfile.defaultProfile().setPersistentStoragePath(BROWSER_STORAGE)

        self.default_font = QFont(BROWSER_FONT_FAMILY)
        self.default_font.setPointSize(BROWSER_FONT_SIZE)
        self.setFont(self.default_font) 

        self.tabs = QTabWidget()
        self.tabs.setIconSize(QSize(13, 13))
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabBar().setExpanding(True)
        self.tabs.tabBar().setAutoHide(1)
        
        self.js_btn_enable = QAction(self.tr("Disable Javascript (Alt+Ctrl+A)"), self)
        self.js_btn_enable.setShortcut("Alt+Ctrl+A")
        icon = QIcon("img/js_enabled.png")
        self.js_btn_enable.setIcon(icon)
        self.js_btn_enable.triggered.connect(lambda: self.javascript_toggle())

        self.js_btn_disable = QAction(self.tr("Enable Javascript (Alt+Ctrl+S)"), self)
        self.js_btn_disable.setShortcut("Alt+Ctrl+S")
        icon = QIcon("img/js_disabled.png")
        self.js_btn_disable.setIcon(icon)
        self.js_btn_disable.setVisible(False)
        self.js_btn_disable.triggered.connect(lambda: self.javascript_toggle())

        self.download_btn = QAction(self.tr("Downloads (Alt+D)"), self)
        self.download_btn.setShortcut("Alt+D")
        icon = QIcon("img/download-item/download-idle.png")
        self.download_btn.setIcon(icon)
        self.download_btn.triggered.connect(lambda: self.download_pressed())

        # Shortcuts 
        self.shortcut_closetab = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_addtab = QShortcut(QKeySequence("Ctrl+J"), self)
        self.shortcut_changetab_f = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut_changetab_b = QShortcut(QKeySequence("Ctrl+H"), self)
        self.shortcut_store_session = QShortcut(QKeySequence("Alt+X"), self)

        self.shortcut_store_session.activated.connect(lambda: bookmark.storeSession(self.current_urls()))
        self.shortcut_closetab.activated.connect(self.close_current_tab)
        self.shortcut_changetab_f.activated.connect(self.tab_change_forward)
        self.shortcut_changetab_b.activated.connect(self.tab_change_back)
        self.shortcut_addtab.activated.connect(self.add_new_tab)
        
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)

        self.setWindowTitle(BROWSER_WINDOW_TITLE)

        if BROWSER_OPEN_URLS:
            for page in BROWSER_OPEN_URLS:
                self.add_new_tab(QUrl(page))
        else:
            self.add_new_tab()
        self.show()

    def add_new_tab(self, qurl=None, label="New Tab", silent=0):
        global default_url_open

        if qurl is None and default_url_open is None:
            if not self.first_opened:
                qurl = QUrl(BROWSER_HOMEPAGE)
                self.first_opened = True
            else:
                qurl = QUrl(BROWSER_NEWTAB)
        if default_url_open is not None: 
            qurl = QUrl(default_url_open)
            qurl.setScheme("http")
            default_url_open = None

        qurl = QUrl(lxu.decodeLynxUrl(qurl))
        browser = QWebEngineView()

        cwe = CustomWebEnginePage(self)
        cwe.set_add_new_tab_h(self.add_new_tab)
        browser.setPage(cwe)

        browser.channel = QWebChannel()
        browser.channel.registerObject('backend', webchannel)
        browser.page().setWebChannel(browser.channel)

        browser.page().setBackgroundColor(QColor(webkit_background_color)) 
        if qurl.toString() != "lynx:blank":
            browser.setUrl(QUrl(qurl))

        if BROWSER_AGENT != None: 
            browser.page().profile().setHttpUserAgent(BROWSER_AGENT)
        browser.settings = self.settings

        htabbox = QVBoxLayout()
        navtb = QToolBar(self.tr("Navigation"))
        navtb.addSeparator() 
        navtb.setMovable(False) 
        navtb.setMaximumHeight(35)
        navtb.setIconSize(QSize(10, 10))

        searchbar = QLineEdit()
        searchbar.returnPressed.connect(lambda: self.search_webview(browser, searchbar.text()))
        searchbar.setFixedHeight(23)
        searchbar.hide()

        # Hidden Buttons - Keyboard Shortcuts
        zoom_in = QPushButton("", self)
        zoom_in.setShortcut("Ctrl++")
        zoom_in.clicked.connect(lambda: self.zoom(0.1, browser))

        zoom_out = QPushButton("", self)
        zoom_out.setShortcut("Ctrl+0")
        zoom_out.clicked.connect(lambda: self.zoom(-0.1, browser))

        save_page = QPushButton("", self)
        save_page.setShortcut("Ctrl+S")
        save_page.clicked.connect(lambda: self.save_page(browser))
        
        mute_page = QPushButton("", self)
        mute_page.setShortcut("Ctrl+M")
        mute_page.clicked.connect(lambda: self.mute_page(browser))
        
        reload_page = QPushButton("", self)
        reload_page.setShortcut("Ctrl+R")
        reload_page.clicked.connect(lambda: browser.reload())
        
        reopen_tab = QPushButton("", self)
        reopen_tab.setShortcut("Ctrl+Shift+T")
        reopen_tab.clicked.connect(lambda: self.open_last())

        close_tab_group = QPushButton("", self)
        close_tab_group.setShortcut("Alt+W")
        close_tab_group.clicked.connect(lambda: self.close_current_tab(-2))

        open_bookmarks_page = QPushButton("", self)
        open_bookmarks_page.setShortcut("Alt+B")
        open_bookmarks_page.clicked.connect(lambda: self.navigate_to_url("lynx:bookmarks", browser))
        
        max_view = QPushButton("", self)
        max_view.setShortcut("Alt+F")
        size = QDesktopWidget().screenGeometry(-1)
        max_view.clicked.connect(lambda: self.resize(size.width(), size.height()))

        search_text = QPushButton("", self)
        search_text.setShortcut("Ctrl+F")
        search_text.clicked.connect(lambda: self.open_searchbar(browser, searchbar))
        
        bookmark_page = QPushButton("", self)
        bookmark_page.setShortcut("Ctrl+B")
        bookmark_page.clicked.connect(lambda: bookmark.addBookmark(browser.page().url().toString(), True))
        
        navtb.addWidget(zoom_in)
        navtb.addWidget(zoom_out)
        navtb.addWidget(save_page)
        navtb.addWidget(mute_page)
        navtb.addWidget(reload_page)
        navtb.addWidget(reopen_tab)
        navtb.addWidget(open_bookmarks_page)
        navtb.addWidget(max_view)
        navtb.addWidget(search_text)
        navtb.addWidget(bookmark_page)
        navtb.addWidget(close_tab_group)

        zoom_in.setMaximumWidth(0)
        zoom_out.setMaximumWidth(0)
        save_page.setMaximumWidth(0)
        mute_page.setMaximumWidth(0)
        reload_page.setMaximumWidth(0)
        reopen_tab.setMaximumWidth(0)
        open_bookmarks_page.setMaximumWidth(0)
        max_view.setMaximumWidth(0)
        search_text.setMaximumWidth(0)
        bookmark_page.setMaximumWidth(0)
        close_tab_group.setMaximumWidth(0)

        back_btn = QAction(self.tr("Back (Alt+J)"), self)
        icon = QIcon("img/remix/arrow-left-s-line.png")
        back_btn.setIcon(icon)
        back_btn.setStatusTip("Back to previous page")
        back_btn.setShortcut('Alt+J')
        back_btn.triggered.connect(lambda: browser.back())

        next_btn = QAction(self.tr("Forward (Alt+K)"), self)
        icon = QIcon("img/remix/arrow-right-s-line.png")
        next_btn.setIcon(icon)
        next_btn.setStatusTip("Forward to next page")
        next_btn.setShortcut('Alt+K')
        next_btn.triggered.connect(lambda: browser.forward())
        navtb.addAction(back_btn)
        navtb.addAction(next_btn)

        secure_icon = QIcon("img/search.png")

        urlbar = QLineEdit()
        urlbar.returnPressed.connect(lambda: self.navigate_to_url(urlbar.text(), browser))
        urlbar.setFixedHeight(26)
        urlbar.addAction(secure_icon, QLineEdit.LeadingPosition);

        completer = QCompleter(bookmark.getBookmarks())
        # urlbar.setCompleter(completer)
        for _ in range(0, 10):
            navtb.addSeparator()
        navtb.addWidget(urlbar)
        
        urlbar_focus = QPushButton("", self)
        urlbar_focus.setShortcut("Ctrl+U")
        urlbar_focus.clicked.connect(lambda: urlbar.setFocus())
        urlbar_focus.setMaximumWidth(0)
        for _ in range(0, 20):
            navtb.addSeparator()
        navtb.addWidget(urlbar_focus)
   
        add_tab_btn = QAction(self.tr("Add Tab (Ctrl+H)"), self)
        icon = QIcon("img/remix/add-line.png")
        add_tab_btn.setIcon(icon)
        add_tab_btn.triggered.connect(lambda: self.add_new_tab())
        navtb.addAction(add_tab_btn)
        navtb.addAction(self.download_btn)

        stealth_btn = QAction(self.tr("Stealth Mode (Alt+S)"), self)
        stealth_btn.setShortcut("Alt+S")
        icon = QIcon("img/remix/spy-line.png")
        stealth_btn.setIcon(icon)
        stealth_btn.triggered.connect(lambda: launch_stealth(self))
        if not STEALTH_FLAG:
            navtb.addAction(stealth_btn)
        
        if STEALTH_FLAG:
            navtb.addAction(self.js_btn_enable)
            navtb.addAction(self.js_btn_disable)

        navtb.addSeparator() 
        htabbox.addWidget(navtb)
        htabbox.addWidget(searchbar)
        htabbox.addWidget(browser)
        htabbox.setContentsMargins(0, 6, 0, 0)
        
        tabpanel = QWidget()
        tabpanel.setLayout(htabbox)
        i = self.tabs.addTab(tabpanel, label) 
        tab_i = len(self.tab_indexes)
        self.tab_indexes.append(i)

        self.tabs.setTabPosition(QTabWidget.North)
        if silent != 1:
            self.tabs.setCurrentIndex(i)

        self.fullscreen = 0
        urlbar.setFocus()
        browser.page().fullScreenRequested.connect(lambda request: (request.accept(), self.fullscreen_webview(htabbox, browser)))
        browser.page().loadFinished.connect(lambda: self.load_finished(urlbar, browser))
        browser.page().loadStarted.connect(lambda: self.load_started(urlbar, browser.page().url().toString(), browser))
        browser.page().titleChanged.connect(lambda _, i = i, browser = browser: self.tabs.setTabText(self.tab_indexes[tab_i], browser.page().title()))
        browser.page().iconChanged.connect(lambda: self.set_tab_icon(self.tab_indexes[tab_i], browser.page()))
        browser.page().loadProgress.connect(lambda p: self.load_progress(p, urlbar, browser.page().url().toString()))
        browser.page().profile().downloadRequested.connect(self.download_item_requested)

        urlbar.textEdited.connect(lambda: self.update_index(self.tabs.currentIndex(), tab_i))

    def closeEvent(self, event):
        lxu.lynxQuit()
        event.accept()

    def load_started(self, urlbar, url, browser):
        if url[:5] == "file:":
            setPrivileges("*")
            return
        setPrivileges()

    def load_finished(self, urlbar, browser):
        if getPriveleges():
            return
        extension.pageLoad(browser)
        self.update_urlbar(urlbar, browser.page().url())

    def update_urlbar(self, urlbar, qurl):
        url = lxu.encodeLynxUrl(qurl)
        urlbar.setText(url)

        icon = None
        if "lynx:" == urlbar.text()[:5]:
            icon = QIcon("img/search.png")
        if urlbar.text() == "lynx:home" or urlbar.text() == "lynx:blank":
            urlbar.setText("")
        if "https://" == urlbar.text()[:8]:
            icon = QIcon("img/secure.png")
        if "http://" == urlbar.text()[:7]:
            icon = QIcon("img/unsecure.png")
        if icon != None:
            urlbar.removeAction(urlbar.actions()[0])
            urlbar.addAction(icon, QLineEdit.LeadingPosition);

    def update_index(self, i, ti):
        self.tab_indexes[ti] = i
    
    def current_urls(self):
        open_urls = []
        for i in range(0, self.tabs.count()):
            open_urls.append(self.tabs.widget(i).findChildren(QWebEngineView)[0].url().toString())
        return open_urls

    def fullscreen_webview(self, htabbox, browser):
        if self.fullscreen == 0:
            self.winsize = self.geometry()
            browser.setParent(None)
            browser.showFullScreen()
            self.fullscreen = 1
            self.settings.setAttribute(QWebEngineSettings.ShowScrollBars, 0)
            self.hide()
        else:
            htabbox.addWidget(browser) 
            browser.showNormal()
            self.show()
            self.setGeometry(self.winsize)
            self.settings.setAttribute(QWebEngineSettings.ShowScrollBars, 1)
            self.fullscreen = 0
    
    def open_searchbar(self, browser, searchbar):
        if searchbar.isHidden():
            searchbar.show()
            searchbar.setFocus()
        else:
            browser.findText("")
            searchbar.setText("")
            searchbar.hide()

    def javascript_toggle(self):
        if self.settings.testAttribute(QWebEngineSettings.JavascriptEnabled):
            self.settings.setAttribute(QWebEngineSettings.JavascriptEnabled, 0)
            self.js_btn_enable.setVisible(False)
            self.js_btn_disable.setVisible(True)
        else: 
            self.settings.setAttribute(QWebEngineSettings.JavascriptEnabled, 1)
            self.js_btn_disable.setVisible(False)
            self.js_btn_enable.setVisible(True)

    def search_webview(self, browser, search):
        browser.findText(search)

    def download_item_progress(self, bytes_received, bytes_total):
        global downloading_item 
        progress = 100
        if bytes_received > 0 and bytes_total > 0:
            progress = 100 * float(bytes_received)/float(bytes_total)

        images = {20:"download-20", 40:"download-40", 60:"download-60", 80:"download-80", 90:"download-100", 100:"download-done"}
        set_picture = "download-idle"
        for i, val in enumerate(list(images.keys())):
            if progress >= val:
                set_picture = list(images.values())[i]
        if progress >= 100:
            downloading_item = False 

        icon = QIcon("img/download-item/" + set_picture + ".png")
        self.download_btn.setIcon(icon)
        if not downloading_item:
            QTimer.singleShot(1000, lambda: self.download_btn.setIcon(QIcon("img/download-item/download-reset.png")))

    def download_pressed(self):
        global download_directory
        open_folder(download_directory)

    def download_item_requested(self, download):
        global download_directory, downloading_item
        if not downloading_item:
            path = str(QFileDialog.getSaveFileName(self, 'Open file', DOWNLOAD_PATH + os.path.basename(download.path()), "All Files(*)")[0])
            download.downloadProgress.connect(self.download_item_progress)
            download.setPath(path)
            if download.path() == path:
                download_directory = os.path.dirname(path)
            downloading_item = True 
            download.accept()

    def zoom(self, value, browser):
        changezoom = 0
        if value > 0:
            if browser.zoomFactor() < 4.9:
                changezoom = browser.zoomFactor() + value
        if value < 0:
            if browser.zoomFactor() > .39:
                changezoom = browser.zoomFactor() + value
        browser.setZoomFactor(changezoom)
    
    def save_page(self, browser):
        destination = QFileDialog.getSaveFileName(self, self.tr("Save Page"), DOWNLOAD_PATH + browser.page().title() + ".html", "*.html")
        if destination:
            browser.page().save(destination[0], QWebEngineDownloadItem.SingleHtmlSaveFormat)

    def mute_page(self, browser):
        if browser.page().isAudioMuted():
            browser.page().setAudioMuted(0)
        else:
            browser.page().setAudioMuted(1)

    def set_tab_icon(self, i, webpage):
        if webpage.icon():
            self.tabs.setTabIcon(i, webpage.icon())

    def tab_open_doubleclick(self, i):
        if i == -1:
            self.add_new_tab()

    def open_last(self):
        if self.last_closed_tab:
            self.add_new_tab(self.last_closed_tab)

    def close_current_tab(self, i=-1):
        index = i
        if i == -1 or i == -2:
            index = self.tabs.currentIndex()
        if self.tabs.count() < 2:
            lxu.lynxQuit()
            QApplication.quit()

        if i == -2:
            for _ in range(0, index):
                self.close_current_tab(0)
            while self.tabs.count() > 1:
                self.close_current_tab(1)
            return

        self.last_closed_tab = self.tabs.widget(index).findChildren(QWebEngineView)[0].url()
        self.tabs.widget(index).findChildren(QWebEngineView)[0].page().setParent(None)
        self.tabs.widget(index).deleteLater()
        self.tabs.removeTab(index)

    def tab_change_forward(self):
        self.tabs.setCurrentIndex(self.tabs.currentIndex()+1)
    
    def tab_change_back(self):
        self.tabs.setCurrentIndex(self.tabs.currentIndex()-1)

    def navigate_home(self):
        self.tabs.currentWidget().setUrl(QUrl(BROWSER_HOMEPAGE))

    def navigate_to_url(self, url, webview):
        if url == "":
            return
        _qurl = QUrl(url)
        if "." not in url and not lxu.checkLynxUrl(_qurl):
            _qurl = QUrl("https://duckduckgo.com/?q=" + url)
        elif "." in url and not lxu.checkLynxUrl(_qurl) and not "file:///" in url:
            _qurl.setScheme("http")

        _qurl = QUrl(lxu.decodeLynxUrl(_qurl))
        webview.setUrl(_qurl)

    def load_progress(self, progress, urlbar, url):
        global progress_color_loading
        if url[:5] == "file:" or not url:
            urlbar.setStyleSheet('background-color: ;')
            return
        if progress < 99:
            percent = progress / 100
            urlbar.setStyleSheet('background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop: 0 ' + progress_color_loading + ', stop: ' + str(percent) + ' ' + progress_color_loading + ', stop: ' + str(percent + 0.001) + ' rgba(0, 0, 0, 0), stop: 1 #00000005)')
        else:
            urlbar.setStyleSheet('background-color: ;')
