import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1500
    height: 900
    minimumWidth: 1050
    minimumHeight: 680
    visible: true
    title: "Beta Draft"
    color: "#10151b"
    palette.window: "#10151b"
    palette.windowText: "#f3f5f7"
    palette.base: "#171d24"
    palette.text: "#e8edf2"
    palette.button: "#28323d"
    palette.buttonText: "#f3f5f7"
    palette.highlight: "#2f83c5"
    palette.highlightedText: "#ffffff"
    palette.toolTipBase: "#28323d"
    palette.toolTipText: "#f3f5f7"
    palette.placeholderText: "#7f8d9b"

    readonly property var emptyUi: ({
        "heading": "",
        "subheading": "",
        "message": "",
        "complete": false,
        "pack": [],
        "poolGroups": [],
        "poolCount": 0,
        "preview": ({}),
        "packStyle": "",
        "advisorEnabled": false,
        "advisorPickName": "",
        "scoreDisplayEnabled": false,
        "colorPlanDisplayEnabled": false,
        "colorPlans": [],
        "noBasicLands": false,
        "colorBalanced": false,
        "tableSize": 8,
        "rounds": 3
    })
    property var ui: typeof draftBridge !== "undefined" && draftBridge !== null
        ? draftBridge.state : emptyUi

    component DarkButton: Button {
        id: darkButton
        hoverEnabled: true
        implicitHeight: 38
        implicitWidth: Math.max(100, buttonLabel.implicitWidth + 28)

        contentItem: Text {
            id: buttonLabel
            text: darkButton.text
            color: darkButton.enabled ? "#f3f5f7" : "#768392"
            font.pixelSize: 14
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 6
            color: !darkButton.enabled ? "#1d242c"
                : darkButton.down ? "#202a34"
                : darkButton.hovered ? "#354353" : "#28323d"
            border.color: darkButton.activeFocus ? "#62ddc7" : "#526172"
            border.width: darkButton.activeFocus ? 2 : 1
        }
    }

    component DarkCheckBox: AbstractButton {
        id: darkCheckBox
        checkable: true
        hoverEnabled: true
        focusPolicy: Qt.StrongFocus
        spacing: 7
        leftPadding: 0
        rightPadding: 2
        topPadding: 6
        bottomPadding: 6
        implicitHeight: 32
        implicitWidth: checkBoxContent.implicitWidth + leftPadding + rightPadding

        Accessible.role: Accessible.CheckBox
        Accessible.name: text
        Accessible.checked: checked

        contentItem: Row {
            id: checkBoxContent
            spacing: darkCheckBox.spacing

            Rectangle {
                id: checkIndicator
                width: 20
                height: 20
                radius: 4
                color: darkCheckBox.checked
                    ? (darkCheckBox.enabled ? "#267fc0" : "#354d60")
                    : "#151b21"
                border.color: darkCheckBox.activeFocus ? "#62ddc7"
                    : darkCheckBox.hovered && darkCheckBox.enabled
                        ? "#8fc7ec" : "#536273"
                border.width: darkCheckBox.activeFocus ? 2 : 1

                Canvas {
                    id: checkMark
                    anchors.fill: parent
                    visible: darkCheckBox.checked
                    property color markColor: darkCheckBox.enabled
                        ? "#ffffff" : "#8995a1"
                    onMarkColorChanged: requestPaint()
                    onVisibleChanged: requestPaint()
                    onPaint: {
                        const context = getContext("2d")
                        context.clearRect(0, 0, width, height)
                        context.strokeStyle = markColor
                        context.lineWidth = 2.2
                        context.lineCap = "round"
                        context.lineJoin = "round"
                        context.beginPath()
                        context.moveTo(5, 10)
                        context.lineTo(8.5, 13.5)
                        context.lineTo(15, 6.5)
                        context.stroke()
                    }
                }
            }

            Text {
                id: checkLabel
                anchors.verticalCenter: parent.verticalCenter
                text: darkCheckBox.text
                color: darkCheckBox.enabled ? "#dce5ed" : "#778492"
                font.pixelSize: 14
            }
        }

        background: Item {}
    }

    component NumberStepper: Row {
        id: numberStepper
        property int value: 1
        property int minimumValue: 1
        property int maximumValue: 99
        spacing: 8

        DarkButton {
            implicitWidth: 38
            text: "-"
            enabled: numberStepper.value > numberStepper.minimumValue
            Accessible.name: "Decrease"
            onClicked: numberStepper.value--
        }
        Rectangle {
            width: 52
            height: 38
            radius: 6
            color: "#11171d"
            border.color: "#465565"

            Text {
                anchors.centerIn: parent
                text: numberStepper.value
                color: "#f3f5f7"
                font.pixelSize: 16
                font.bold: true
            }
        }
        DarkButton {
            implicitWidth: 38
            text: "+"
            enabled: numberStepper.value < numberStepper.maximumValue
            Accessible.name: "Increase"
            onClicked: numberStepper.value++
        }
    }

    component DarkScrollBar: ScrollBar {
        id: darkScrollBar
        policy: ScrollBar.AsNeeded
        contentItem: Rectangle {
            implicitWidth: 7
            implicitHeight: 7
            radius: 4
            color: darkScrollBar.pressed ? "#8fc7ec"
                : darkScrollBar.hovered ? "#70869b" : "#4c5d6e"
            opacity: darkScrollBar.active ? 0.95 : 0.58
        }
        background: Rectangle {
            color: "transparent"
        }
    }

    component DarkToolTip: ToolTip {
        id: darkToolTip
        padding: 8
        contentItem: Text {
            text: darkToolTip.text
            color: "#f3f5f7"
            font.pixelSize: 12
        }
        background: Rectangle {
            radius: 5
            color: "#28323d"
            border.color: "#596a7b"
            border.width: 1
        }
    }

    component CardTile: Item {
        id: tile
        required property var cardData
        property bool canDraft: false
        property bool hasArt: cardData.artCropUrl
            && cardData.artCropUrl.toString().length > 0
        signal inspectRequested(string cardId)
        signal draftRequested(string cardId)

        width: 154
        height: 108

        Rectangle {
            id: cardFrame
            anchors.fill: parent
            anchors.margins: 3
            radius: 7
            color: tile.cardData.background
            border.color: tile.cardData.border
            border.width: 3
        }

        Rectangle {
            anchors.fill: cardFrame
            anchors.margins: 4
            radius: 5
            color: tile.cardData.background
            clip: true

            Image {
                anchors.fill: parent
                source: tile.cardData.artCropUrl || ""
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                cache: true
                smooth: true
                mipmap: true
                visible: tile.hasArt && status !== Image.Error
            }
        }

        Rectangle {
            anchors.fill: cardFrame
            anchors.margins: 5
            radius: 5
            color: "transparent"
            border.color: Qt.rgba(1, 1, 1, 0.24)
            border.width: 1
        }

        Rectangle {
            anchors.fill: parent
            radius: 9
            color: "transparent"
            border.color: hoverArea.containsMouse ? "#f2ca62" : "#62ddc7"
            border.width: 3
            visible: hoverArea.containsMouse || tile.cardData.botRecommended
            z: 20
        }

        Text {
            id: cost
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 9
            text: tile.cardData.manaCost
            color: tile.hasArt ? "white" : tile.cardData.foreground
            font.pixelSize: 15
            font.bold: true
            style: tile.hasArt ? Text.Outline : Text.Normal
            styleColor: "#d9000000"
        }

        Text {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: cost.left
            anchors.margins: 9
            text: tile.cardData.name
            color: tile.hasArt ? "white" : tile.cardData.foreground
            font.pixelSize: 16
            font.bold: true
            style: tile.hasArt ? Text.Outline : Text.Normal
            styleColor: "#d9000000"
            wrapMode: Text.Wrap
            maximumLineCount: 3
            elide: Text.ElideRight
        }

        Text {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.margins: 9
            text: tile.cardData.rarity.substring(0, 1)
            color: tile.hasArt ? "white" : tile.cardData.foreground
            font.pixelSize: 12
            opacity: 0.72
            visible: !tile.cardData.botRecommended
                && !(tile.cardData.botScoreText || "")
            style: tile.hasArt ? Text.Outline : Text.Normal
            styleColor: "#d9000000"
        }

        Rectangle {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.leftMargin: 7
            anchors.bottomMargin: 7
            width: 64
            height: 20
            radius: 5
            visible: tile.cardData.botRecommended
                && !(tile.cardData.botScoreText || "")
            color: "#17463f"
            border.color: "#62ddc7"

            Text {
                anchors.centerIn: parent
                text: "BOT PICK"
                color: "#d8fff8"
                font.pixelSize: 10
                font.bold: true
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.leftMargin: 7
            anchors.bottomMargin: 7
            width: tile.cardData.botRecommended ? 78 : 58
            height: 20
            radius: 5
            visible: (tile.cardData.botScoreText || "").length > 0
            color: tile.cardData.botRecommended ? "#17463f" : "#202a34"
            border.color: tile.cardData.botRecommended ? "#62ddc7" : "#8293a4"

            Text {
                anchors.centerIn: parent
                text: (tile.cardData.botRecommended ? "BEST " : "")
                    + (tile.cardData.botScoreText || "")
                color: tile.cardData.botRecommended ? "#d8fff8" : "#edf2f6"
                font.pixelSize: 10
                font.bold: true
            }
        }

        Text {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 9
            text: tile.cardData.stats
            color: tile.hasArt ? "white" : tile.cardData.foreground
            font.pixelSize: 15
            font.bold: tile.hasArt
            style: tile.hasArt ? Text.Outline : Text.Normal
            styleColor: "#d9000000"
        }

        MouseArea {
            id: hoverArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: tile.canDraft ? Qt.PointingHandCursor : Qt.ArrowCursor
            onEntered: tile.inspectRequested(tile.cardData.id)
            onDoubleClicked: if (tile.canDraft) tile.draftRequested(tile.cardData.id)
        }

        DarkToolTip {
            visible: hoverArea.containsMouse && tile.canDraft
            text: "Double-click to draft"
            delay: 650
        }
    }

    component ZonePanel: Rectangle {
        color: "#171d24"
        radius: 10
        border.color: "#3d4a58"
        border.width: 1
    }

    component PoolCard: Item {
        id: poolCard
        required property var cardData
        property bool hasArt: cardData.artCropUrl
            && cardData.artCropUrl.toString().length > 0
        signal inspectRequested(string cardId)

        width: 126
        height: 78

        Rectangle {
            id: poolCardFrame
            anchors.fill: parent
            anchors.margins: 3
            radius: 6
            color: poolCard.cardData.background
            border.color: poolCard.cardData.border
            border.width: 3
        }

        Rectangle {
            anchors.fill: poolCardFrame
            anchors.margins: 4
            radius: 4
            color: poolCard.cardData.background
            clip: true

            Image {
                anchors.fill: parent
                source: poolCard.cardData.artCropUrl || ""
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                cache: true
                smooth: true
                mipmap: true
                visible: poolCard.hasArt && status !== Image.Error
            }
        }

        Rectangle {
            anchors.fill: poolCardFrame
            anchors.margins: 4
            radius: 4
            color: "transparent"
            border.color: Qt.rgba(1, 1, 1, 0.22)
        }
        Rectangle {
            anchors.fill: parent
            radius: 8
            color: "transparent"
            border.color: "#f2ca62"
            border.width: 3
            visible: poolHover.containsMouse
            z: 20
        }
        Text {
            anchors.left: parent.left
            anchors.right: poolCost.left
            anchors.top: parent.top
            anchors.leftMargin: 7
            anchors.topMargin: 6
            anchors.rightMargin: 4
            text: poolCard.cardData.name
            color: poolCard.hasArt ? "white" : poolCard.cardData.foreground
            font.pixelSize: 13
            font.bold: true
            style: poolCard.hasArt ? Text.Outline : Text.Normal
            styleColor: "#d9000000"
            elide: Text.ElideRight
            maximumLineCount: 1
        }
        Text {
            id: poolCost
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: 7
            anchors.topMargin: 6
            text: poolCard.cardData.manaCost
            color: poolCard.hasArt ? "white" : poolCard.cardData.foreground
            font.pixelSize: 12
            font.bold: true
            style: poolCard.hasArt ? Text.Outline : Text.Normal
            styleColor: "#d9000000"
        }
        Text {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 7
            text: poolCard.cardData.stats
            color: poolCard.hasArt ? "white" : poolCard.cardData.foreground
            font.pixelSize: 13
            font.bold: poolCard.hasArt
            style: poolCard.hasArt ? Text.Outline : Text.Normal
            styleColor: "#d9000000"
        }
        MouseArea {
            id: poolHover
            anchors.fill: parent
            hoverEnabled: true
            onEntered: poolCard.inspectRequested(poolCard.cardData.id)
        }
    }

    Popup {
        id: draftSettings
        objectName: "draftSettings"
        width: Math.min(520, window.width - 48)
        height: 500
        x: Math.round((window.width - width) / 2)
        y: Math.round((window.height - height) / 2)
        padding: 22
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape

        onAboutToShow: {
            noBasicsToggle.checked = window.ui.noBasicLands
            balancedCommonsToggle.checked = window.ui.colorBalanced
            playerStepper.value = window.ui.tableSize
            roundStepper.value = window.ui.rounds
        }

        Overlay.modal: Rectangle {
            color: "#99000000"
        }
        background: Rectangle {
            radius: 10
            color: "#1b222a"
            border.color: "#536273"
            border.width: 1
        }
        contentItem: ColumnLayout {
            spacing: 10

            Text {
                Layout.fillWidth: true
                text: "New draft settings"
                color: "#f3f5f7"
                font.pixelSize: 22
                font.bold: true
            }
            Text {
                Layout.fillWidth: true
                text: window.ui.poolCount > 0
                    ? "Starting will replace the current draft and drafted pool."
                    : "Choose the settings for the packs you are about to open."
                color: window.ui.poolCount > 0 ? "#f2ca62" : "#aebccc"
                font.pixelSize: 13
                wrapMode: Text.Wrap
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: "#3d4a58"
            }

            Text {
                text: "Pack generation"
                color: "#dce5ed"
                font.pixelSize: 15
                font.bold: true
            }
            DarkCheckBox {
                id: noBasicsToggle
                text: "Exclude basic lands from booster slots"
            }
            Text {
                Layout.fillWidth: true
                Layout.leftMargin: 27
                text: "Use a modernized rarity pool instead of Beta's historical sheets."
                color: "#8fa0b2"
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }
            DarkCheckBox {
                id: balancedCommonsToggle
                text: "Balance colors in the common slots"
            }
            Text {
                Layout.fillWidth: true
                Layout.leftMargin: 27
                text: "Ensure that every pack's commons represent all five colors."
                color: "#8fa0b2"
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 6

                ColumnLayout {
                    spacing: 1
                    Text {
                        text: "Players"
                        color: "#dce5ed"
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: "Seats at the table, including you"
                        color: "#8fa0b2"
                        font.pixelSize: 12
                    }
                }
                Item { Layout.fillWidth: true }
                NumberStepper {
                    id: playerStepper
                    minimumValue: 2
                    maximumValue: 16
                }
            }
            RowLayout {
                Layout.fillWidth: true

                ColumnLayout {
                    spacing: 1
                    Text {
                        text: "Booster rounds"
                        color: "#dce5ed"
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: "Fifteen picks per round"
                        color: "#8fa0b2"
                        font.pixelSize: 12
                    }
                }
                Item { Layout.fillWidth: true }
                NumberStepper {
                    id: roundStepper
                    minimumValue: 1
                    maximumValue: 10
                }
            }

            Item { Layout.fillHeight: true }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                DarkButton {
                    text: "Cancel"
                    onClicked: draftSettings.close()
                }
                DarkButton {
                    implicitWidth: 142
                    text: "Start new draft"
                    onClicked: {
                        draftBridge.startNewDraft(
                            noBasicsToggle.checked,
                            balancedCommonsToggle.checked,
                            playerStepper.value,
                            roundStepper.value
                        )
                        draftSettings.close()
                    }
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 14

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            ZonePanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 78

                Item {
                    anchors.fill: parent

                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 20
                        anchors.right: draftActions.left
                        anchors.rightMargin: 14
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3

                        Text {
                            width: parent.width
                            text: window.ui.heading
                            color: "#f3f5f7"
                            font.pixelSize: 24
                            font.bold: true
                            elide: Text.ElideRight
                        }
                        Text {
                            width: parent.width
                            text: window.ui.subheading + " · " + window.ui.packStyle
                            color: "#aebccc"
                            font.pixelSize: 14
                            elide: Text.ElideRight
                        }
                    }

                    Row {
                        id: draftActions
                        objectName: "draftActions"
                        anchors.right: parent.right
                        anchors.rightMargin: 14
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 14

                        DarkButton {
                            text: "New draft..."
                            onClicked: draftSettings.open()
                        }
                    }
                }
            }

            ZonePanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 300

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 9

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: window.ui.complete ? "No pack remaining" : "Current pack"
                            color: "#f3f5f7"
                            font.pixelSize: 18
                            font.bold: true
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            visible: !window.ui.complete
                            Layout.preferredWidth: 280
                            Layout.minimumWidth: 120
                            Layout.maximumWidth: 280
                            text: window.ui.advisorEnabled
                                ? "Bot recommends " + window.ui.advisorPickName
                                : "Double-click your pick"
                            color: window.ui.advisorEnabled ? "#62ddc7" : "#f2ca62"
                            font.pixelSize: 13
                            horizontalAlignment: Text.AlignRight
                            elide: Text.ElideRight
                        }
                        DarkCheckBox {
                            id: advisorToggle
                            objectName: "advisorToggle"
                            visible: !window.ui.complete
                            checked: window.ui.advisorEnabled
                            text: "Show bot pick"
                            onToggled: draftBridge.setAdvisorEnabled(checked)
                        }
                        DarkCheckBox {
                            id: scoreToggle
                            objectName: "scoreToggle"
                            visible: !window.ui.complete
                            checked: window.ui.scoreDisplayEnabled
                            text: "Show scores"
                            onToggled: draftBridge.setScoreDisplayEnabled(checked)
                        }
                    }

                    Flickable {
                        id: packScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: width
                        contentHeight: packFlow.height
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: DarkScrollBar {}

                        Flow {
                            id: packFlow
                            // Keep a narrow gutter for the overlaid scrollbar.
                            // This fixed viewport relationship avoids the
                            // content-width/scrollbar visibility binding loop.
                            width: Math.max(0, packScroll.width - 10)
                            height: childrenRect.height
                            spacing: 11
                            Repeater {
                                model: window.ui.pack
                                delegate: CardTile {
                                    required property var modelData
                                    cardData: modelData
                                    canDraft: true
                                    onInspectRequested: function(cardId) {
                                        draftBridge.inspectCard(cardId)
                                    }
                                    onDraftRequested: function(cardId) {
                                        draftBridge.draftCard(cardId)
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        visible: window.ui.complete
                        Layout.alignment: Qt.AlignHCenter
                        text: "All picks are complete. Your drafted pool is below."
                        color: "#aebccc"
                        font.pixelSize: 17
                    }
                }
            }

            ZonePanel {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(245, window.height * 0.32)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Your picks · " + window.ui.poolCount
                            color: "#f3f5f7"
                            font.pixelSize: 18
                            font.bold: true
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "Color stacks · low to high mana value"
                            color: "#8fa0b2"
                            font.pixelSize: 12
                        }
                    }

                    ScrollView {
                        id: poolScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: poolRow.width
                        contentHeight: poolRow.height
                        ScrollBar.vertical: DarkScrollBar {}
                        ScrollBar.horizontal: DarkScrollBar {}

                        Row {
                            id: poolRow
                            height: childrenRect.height
                            spacing: 9
                            Repeater {
                                model: window.ui.poolGroups
                                delegate: Column {
                                    id: colorStack
                                    required property var modelData
                                    width: 126
                                    spacing: 5

                                    Text {
                                        width: parent.width
                                        height: 20
                                        text: colorStack.modelData.label + " · "
                                            + colorStack.modelData.count
                                        color: colorStack.modelData.accent
                                        font.pixelSize: 13
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        elide: Text.ElideRight
                                    }

                                    Item {
                                        width: 126
                                        height: colorStack.modelData.cards.length > 0
                                            ? 78 + (colorStack.modelData.cards.length - 1) * 24
                                            : 34

                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            anchors.top: parent.top
                                            anchors.topMargin: 7
                                            visible: colorStack.modelData.cards.length === 0
                                            text: "—"
                                            color: "#566575"
                                            font.pixelSize: 17
                                        }

                                        Repeater {
                                            model: colorStack.modelData.cards
                                            delegate: PoolCard {
                                                required property var modelData
                                                required property int index
                                                y: index * 24
                                                z: index
                                                cardData: modelData
                                                onInspectRequested: function(cardId) {
                                                    draftBridge.inspectCard(cardId)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.preferredHeight: 22
                text: window.ui.message
                color: "#f2ca62"
                font.pixelSize: 14
                elide: Text.ElideRight
            }
        }

        ZonePanel {
            Layout.preferredWidth: 340
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: "Card preview"
                    color: "#f3f5f7"
                    font.pixelSize: 19
                    font.bold: true
                }

                Rectangle {
                    id: previewCard
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(560, width * 1.392857)
                    radius: 14
                    color: window.ui.preview.background || "#aaa7a1"
                    border.color: window.ui.preview.border || "#66635e"
                    border.width: 4
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 17
                        spacing: 11

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                Layout.fillWidth: true
                                text: window.ui.preview.name || ""
                                color: window.ui.preview.foreground || "#222222"
                                font.pixelSize: 23
                                font.bold: true
                                wrapMode: Text.Wrap
                            }
                            Text {
                                text: window.ui.preview.manaCost || ""
                                color: window.ui.preview.foreground || "#222222"
                                font.pixelSize: 20
                                font.bold: true
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: window.ui.preview.foreground || "#222222"
                            opacity: 0.45
                        }

                        Text {
                            Layout.fillWidth: true
                            text: window.ui.preview.typeLine || ""
                            color: window.ui.preview.foreground || "#222222"
                            font.pixelSize: 15
                            font.bold: true
                            wrapMode: Text.Wrap
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 9
                            color: Qt.rgba(1, 1, 1, 0.16)
                            border.color: Qt.rgba(1, 1, 1, 0.24)

                            ScrollView {
                                anchors.fill: parent
                                anchors.margins: 12
                                clip: true
                                ScrollBar.vertical: DarkScrollBar {}
                                ScrollBar.horizontal: DarkScrollBar {}
                                TextArea {
                                    text: window.ui.preview.rulesText || ""
                                    color: window.ui.preview.foreground || "#222222"
                                    font.pixelSize: 16
                                    wrapMode: Text.Wrap
                                    readOnly: true
                                    selectByMouse: true
                                    background: null
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                Layout.fillWidth: true
                                text: window.ui.preview.rarity || ""
                                color: window.ui.preview.foreground || "#222222"
                                font.pixelSize: 14
                                opacity: 0.75
                            }
                            Text {
                                text: window.ui.preview.stats || ""
                                color: window.ui.preview.foreground || "#222222"
                                font.pixelSize: 21
                                font.bold: true
                            }
                        }
                    }

                    Image {
                        id: fullCardImage
                        anchors.fill: parent
                        z: 2
                        source: window.ui.preview.fullCardUrl || ""
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                        cache: true
                        smooth: true
                        mipmap: true
                        visible: source.toString() !== "" && status !== Image.Error
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: window.ui.preview.colorLabel
                        ? (window.ui.preview.fullCardUrl
                            ? "Full Beta card image"
                            : "Text preview · run the image downloader for card scans")
                        : ""
                    color: "#8fa0b2"
                    font.pixelSize: 13
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 100
                    visible: window.ui.colorPlanDisplayEnabled
                    radius: 8
                    color: "#141a21"
                    border.color: "#3d4a58"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6

                        Text {
                            text: "Bot color plans"
                            color: "#f3f5f7"
                            font.pixelSize: 15
                            font.bold: true
                        }
                        Text {
                            text: "Weighted focus used for the current pack"
                            color: "#8fa0b2"
                            font.pixelSize: 11
                        }
                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 2
                            model: window.ui.colorPlans
                            ScrollBar.vertical: DarkScrollBar {}

                            delegate: Item {
                                required property var modelData
                                width: ListView.view.width
                                height: 18

                                Text {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 38
                                    text: modelData.label
                                    color: "#dce5ed"
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 44
                                    anchors.right: planWeight.left
                                    anchors.rightMargin: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    height: 7
                                    radius: 3
                                    color: "#25303a"

                                    Rectangle {
                                        width: Math.max(2, parent.width * modelData.relativeWeight)
                                        height: parent.height
                                        radius: parent.radius
                                        color: "#62ddc7"
                                    }
                                }
                                Text {
                                    id: planWeight
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 48
                                    text: modelData.weightText
                                    color: "#aebccc"
                                    font.pixelSize: 12
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                        }
                    }
                }
                Item {
                    Layout.fillHeight: true
                    visible: !window.ui.colorPlanDisplayEnabled
                }
            }
        }
    }
}
