import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root

    property string promptText: ""
    property var choices: []
    property bool finishVisible: false
    property bool finishEnabled: true
    property string finishText: "Done"
    property bool cancelVisible: false
    property string cancelText: "Cancel"
    property string emptyText: "No choices are currently available."

    signal choiceSelected(var choiceId)
    signal finishRequested()
    signal cancelRequested()

    anchors.centerIn: parent
    width: Math.min(680, parent ? parent.width - 48 : 680)
    height: Math.min(
        parent ? parent.height - 48 : 520,
        Math.min(520, Math.max(260, 170 + root.choices.length * 48))
    )
    modal: true
    closePolicy: Popup.NoAutoClose

    contentItem: ColumnLayout {
        spacing: 10

        Label {
            visible: root.promptText.length > 0
            text: root.promptText
            color: "#ffffff"
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Frame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            padding: 6
            background: Rectangle {
                color: "#171d24"
                border.color: "#536171"
                radius: 7
            }

            ScrollView {
                id: choiceScroll
                anchors.fill: parent
                clip: true
                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                Column {
                    width: choiceScroll.availableWidth
                    spacing: 6

                    Repeater {
                        model: root.choices
                        delegate: Button {
                            required property var modelData
                            width: parent.width
                            text: modelData.label
                            enabled: modelData.enabled === undefined
                                     ? true : modelData.enabled
                            onClicked: root.choiceSelected(modelData.id)
                        }
                    }

                    Label {
                        visible: root.choices.length === 0
                        width: parent.width
                        text: root.emptyText
                        color: "#bfc7d1"
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        padding: 18
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.cancelVisible || root.finishVisible

            Button {
                visible: root.cancelVisible
                text: root.cancelText
                onClicked: root.cancelRequested()
            }
            Item { Layout.fillWidth: true }
            Button {
                visible: root.finishVisible
                enabled: root.finishEnabled
                text: root.finishText
                onClicked: root.finishRequested()
            }
        }
    }
}
