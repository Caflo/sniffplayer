import winrt.windows.ui.notifications as notifications
import winrt.windows.data.xml.dom as dom

class Notifier:
    # TODO implement a cross-platform solution
    def __init__(self) -> None:
        self.app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'
        self.nManager = notifications.ToastNotificationManager
        self.notifier = self.nManager.create_toast_notifier(self.app)

    def notify_sniffer_schedule(self, title, content):
        doc = self.__create_xml_string(title, content)
        #display notification
        self.notifier.show(notifications.ToastNotification(doc))

    def __create_xml_string(self, title, content):
        tString = f"""
        <toast>
            <visual>
            <binding template='ToastGeneric'>
                <text>{title}</text>
                <text>{content}</text>
            </binding>
            </visual>
            <actions>
            <action
                content="Dismiss"
                arguments="action=dismiss"/>
            </actions>        
        </toast>
        """
        # convert notification to an XmlDocument
        xDoc = dom.XmlDocument()
        xDoc.load_xml(tString)
        return xDoc