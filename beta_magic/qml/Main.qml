import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1740
    height: 900
    minimumWidth: 1250
    minimumHeight: 700
    title: "Beta Magic · Rules Engine"
    color: "#101419"

    property var gameState: gameBridge.state
    property var inspectedCard: null

    Dialog {
        id: counterRewindDialog
        anchors.centerIn: parent
        width: 390
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.counterRewindRequired
        title: "Rewind " + gameState.counterRewindCard
        onOpened: counterRewindAmount.value = gameState.counterRewindMaximum

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: gameState.counterRewindCanChoose
                      ? "Choose how many lost +1/+0 counters to replace for 1 mana each. Replacing any counters leaves the Beast tapped."
                      : "Waiting for the active player to choose."
                color: "#ffffff"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            SpinBox {
                id: counterRewindAmount
                visible: gameState.counterRewindCanChoose
                from: 0
                to: gameState.counterRewindMaximum
                value: gameState.counterRewindMaximum
                Layout.alignment: Qt.AlignHCenter
            }
            Button {
                visible: gameState.counterRewindCanChoose
                text: counterRewindAmount.value === 0
                      ? "Untap normally" : "Replace counters"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.chooseCounterRewind(counterRewindAmount.value)
            }
            Button {
                visible: !gameState.counterRewindCanChoose
                text: "Switch perspective"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.switchPerspective()
            }
        }
    }

    Dialog {
        id: partialUpkeepDialog
        anchors.centerIn: parent
        width: 390
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.partialUpkeepRequired
        title: "Choose upkeep payment"
        onOpened: partialUpkeepAmount.value = gameState.partialUpkeepAffordable

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: gameState.partialUpkeepPlayer === gameState.perspective.id
                      ? "Choose how much mana to pay. You will take 1 damage "
                        + "for each of the " + gameState.partialUpkeepMaximum
                        + " mana left unpaid."
                      : "Waiting for the affected player to choose a payment."
                color: "#ffffff"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            SpinBox {
                id: partialUpkeepAmount
                visible: gameState.partialUpkeepPlayer === gameState.perspective.id
                from: 0
                to: gameState.partialUpkeepAffordable
                value: gameState.partialUpkeepAffordable
                editable: false
                Layout.alignment: Qt.AlignHCenter
            }
            Label {
                visible: partialUpkeepAmount.visible
                text: "Pay " + partialUpkeepAmount.value + " mana; take "
                      + (gameState.partialUpkeepMaximum - partialUpkeepAmount.value)
                      + " damage"
                color: "#ffd978"
                Layout.alignment: Qt.AlignHCenter
            }
            Button {
                visible: partialUpkeepAmount.visible
                text: "Confirm payment"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.choosePartialUpkeepPayment(
                    partialUpkeepAmount.value
                )
            }
            Button {
                visible: gameState.partialUpkeepPlayer !== gameState.perspective.id
                text: "Switch perspective"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.switchPerspective()
            }
        }
    }

    Dialog {
        anchors.centerIn: parent
        width: 420
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.counterPurchaseRequired
        title: "Grow heads on " + gameState.counterPurchaseCard
        onOpened: counterPurchaseAmount.value = gameState.counterPurchaseMaximum
        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: gameState.counterPurchasePlayer === gameState.perspective.id
                      ? "Choose how many head counters to grow for RRR each."
                      : "Waiting for the active player to choose."
                color: "#ffffff"; wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
            SpinBox {
                id: counterPurchaseAmount
                visible: gameState.counterPurchasePlayer === gameState.perspective.id
                from: 0; to: gameState.counterPurchaseMaximum
                value: gameState.counterPurchaseMaximum
                Layout.alignment: Qt.AlignHCenter
            }
            Button {
                visible: counterPurchaseAmount.visible
                text: counterPurchaseAmount.value ? "Grow heads" : "Grow no heads"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.chooseUpkeepCounterPurchase(counterPurchaseAmount.value)
            }
            Button {
                visible: !counterPurchaseAmount.visible
                text: "Switch perspective"; Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.switchPerspective()
            }
        }
    }

    Dialog {
        anchors.centerIn: parent
        width: 430
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.counterDamageRequired
        title: gameState.counterDamageCard + " takes damage"
        onOpened: counterDamageAmount.value = gameState.counterDamageMaximum
        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: gameState.counterDamagePlayer === gameState.perspective.id
                      ? gameState.counterDamageAmount + " damage will be absorbed by heads. Pay R for each head to preserve; unpaid heads are removed."
                      : "Waiting for the creature's controller to choose."
                color: "#ffffff"; wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
            SpinBox {
                id: counterDamageAmount
                visible: gameState.counterDamagePlayer === gameState.perspective.id
                from: 0; to: gameState.counterDamageMaximum
                value: gameState.counterDamageMaximum
                Layout.alignment: Qt.AlignHCenter
            }
            Button {
                visible: counterDamageAmount.visible
                text: "Confirm red mana payment"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.chooseCounterDamagePayment(counterDamageAmount.value)
            }
            Button {
                visible: !counterDamageAmount.visible
                text: "Switch perspective"; Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.switchPerspective()
            }
        }
    }

    Dialog {
        id: drainPowerDialog
        anchors.centerIn: parent
        width: 390
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.drainPowerChoice
        title: "Drain Power — " + gameState.drainPowerLand

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: gameState.drainPowerCanChoose
                      ? "Choose the mana produced by " + gameState.drainPowerLand + "."
                      : "Waiting for " + gameState.drainPowerChooser
                        + " to choose mana."
                color: "#ffffff"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Repeater {
                model: gameState.drainPowerCanChoose
                       ? gameState.drainPowerManaChoices : []
                Button {
                    required property var modelData
                    text: "Add " + modelData.label
                    Layout.fillWidth: true
                    onClicked: gameBridge.chooseDrainPowerMana(modelData.color)
                }
            }
            Button {
                visible: !gameState.drainPowerCanChoose
                text: "Switch to " + gameState.drainPowerChooser
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.switchPerspective()
            }
        }
    }

    Dialog {
        id: powerSinkDialog
        anchors.centerIn: parent
        width: 420
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.powerSinkPayment
        title: "Power Sink — mandatory payment"

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: gameState.powerSinkCanChoose
                      ? "Choose a land to tap. " + gameState.powerSinkRemaining
                        + " more mana must be paid."
                      : "Waiting for " + gameState.powerSinkPayer
                        + " to pay " + gameState.powerSinkRemaining + " mana."
                color: "#ffffff"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Repeater {
                model: gameState.powerSinkCanChoose
                       ? gameState.powerSinkManaChoices : []
                Button {
                    required property var modelData
                    text: modelData.label
                    Layout.fillWidth: true
                    onClicked: gameBridge.choosePowerSinkMana(
                        modelData.landId, modelData.abilityIndex
                    )
                }
            }
            Button {
                visible: !gameState.powerSinkCanChoose
                text: "Switch to " + gameState.powerSinkPayer
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.switchPerspective()
            }
        }
    }

    Dialog {
        id: handRevealDialog
        anchors.centerIn: parent
        width: Math.min(760, window.width - 48)
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.handRevealPending
        title: gameState.handRevealCanView
               ? "Looking at " + gameState.handRevealTarget + "'s hand"
               : "Private hand reveal"

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                visible: !gameState.handRevealCanView
                text: gameState.handRevealViewer
                      + " may look at " + gameState.handRevealTarget + "'s hand."
                color: "#ffd978"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            CardFlow {
                visible: gameState.handRevealCanView
                Layout.fillWidth: true
                Layout.preferredHeight: implicitHeight
                cards: gameState.handRevealCards
                interactive: false
                onInspected: function(cardData) { window.inspectedCard = cardData }
            }
            Label {
                visible: gameState.handRevealCanView
                         && gameState.handRevealCards.length === 0
                text: gameState.handRevealTarget + " has no cards in hand."
                color: "#ffffff"
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    visible: !gameState.handRevealCanView
                    text: "Switch to " + gameState.handRevealViewer
                    onClicked: gameBridge.switchPerspective()
                }
                Button {
                    visible: gameState.handRevealCanView
                    text: "Done"
                    onClicked: gameBridge.finishHandReveal()
                }
            }
        }
    }

    Dialog {
        id: timeVaultPicker
        anchors.centerIn: parent
        implicitWidth: 420
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.timeVaultChoice
        title: gameState.timeVaultPlayer + "'s upcoming turn"

        contentItem: ColumnLayout {
            spacing: 8
            Label {
                text: "Take the turn, or skip it to ready one Time Vault on your following turn."
                color: "#ffffff"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Repeater {
                model: gameState.timeVaultChoices
                Button {
                    required property var modelData
                    text: modelData.label
                    Layout.fillWidth: true
                    onClicked: gameBridge.chooseTimeVaultTurn(modelData.id)
                }
            }
            Button {
                text: "Take the turn"
                Layout.fillWidth: true
                onClicked: gameBridge.chooseTimeVaultTurn("")
            }
        }
    }

    Dialog {
        id: islandSanctuaryPicker
        anchors.centerIn: parent
        width: 420
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.drawSkipChoice
        title: "Island Sanctuary"
        onOpened: sanctuarySkipAmount.value = gameState.drawSkipMaximum

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: gameState.drawSkipPlayer === gameState.perspective.id
                      ? "Choose how many of your " + gameState.drawSkipTotal
                        + " draw-phase draw(s) to skip. Skipping at least one protects you until your next turn."
                      : "Waiting for the active player to choose their draws."
                color: "#ffffff"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            SpinBox {
                id: sanctuarySkipAmount
                visible: gameState.drawSkipPlayer === gameState.perspective.id
                from: 0
                to: gameState.drawSkipMaximum
                value: gameState.drawSkipMaximum
                editable: false
                Layout.alignment: Qt.AlignHCenter
            }
            Button {
                visible: sanctuarySkipAmount.visible
                text: sanctuarySkipAmount.value
                      ? "Skip " + sanctuarySkipAmount.value + " draw"
                        + (sanctuarySkipAmount.value === 1 ? "" : "s")
                      : "Draw all cards"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.chooseDrawSkips(sanctuarySkipAmount.value)
            }
            Button {
                visible: gameState.drawSkipPlayer !== gameState.perspective.id
                text: "Switch perspective"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.switchPerspective()
            }
        }
    }

    Dialog {
        id: netherShadowPicker
        anchors.centerIn: parent
        width: 440
        modal: false
        closePolicy: Popup.NoAutoClose
        visible: gameState.graveyardReturnChoice
        title: "Nether Shadow"

        contentItem: ColumnLayout {
            spacing: 10
            Label {
                text: gameState.graveyardReturnPlayer === gameState.perspective.id
                      ? "Return an eligible Nether Shadow for BB, or finish making returns for this upkeep. You may activate mana abilities first."
                      : "Waiting for the active player to choose a graveyard return."
                color: "#ffffff"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Repeater {
                model: gameState.graveyardReturnPlayer === gameState.perspective.id
                       ? gameState.graveyardReturnCards : []
                Button {
                    required property var modelData
                    text: "Return " + modelData.name + " (BB)"
                    Layout.fillWidth: true
                    onHoveredChanged: {
                        if (hovered)
                            window.inspectedCard = modelData
                    }
                    onClicked: gameBridge.returnGraveyardCard(modelData.id)
                }
            }
            Button {
                visible: gameState.graveyardReturnPlayer === gameState.perspective.id
                text: "No more returns"
                Layout.fillWidth: true
                onClicked: gameBridge.finishGraveyardReturns()
            }
            Button {
                visible: gameState.graveyardReturnPlayer !== gameState.perspective.id
                text: "Switch perspective"
                Layout.fillWidth: true
                onClicked: gameBridge.switchPerspective()
            }
        }
    }

    Dialog {
        id: graveyardOrderPicker
        anchors.centerIn: parent
        width: 480
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.graveyardOrderChoice
        title: "Order simultaneous graveyard cards"

        contentItem: ColumnLayout {
            spacing: 10
            Label {
                text: gameState.graveyardOrderPlayer === gameState.perspective.id
                      ? "Arrange these cards from bottom to top. The final row will be the top card of your graveyard."
                      : "Waiting for the graveyard's owner to choose an order."
                color: "#ffffff"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Repeater {
                model: gameState.graveyardOrderPlayer === gameState.perspective.id
                       ? gameState.graveyardOrderCards : []
                RowLayout {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    Label {
                        text: (index === 0 ? "Bottom: " : index === gameState.graveyardOrderCards.length - 1 ? "Top: " : "") + modelData.name
                        color: "#ffffff"
                        Layout.fillWidth: true
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: window.inspectedCard = modelData
                        }
                    }
                    Button {
                        text: "Down"
                        enabled: index > 0
                        onClicked: gameBridge.moveGraveyardOrderCard(modelData.id, -1)
                    }
                    Button {
                        text: "Up"
                        enabled: index < gameState.graveyardOrderCards.length - 1
                        onClicked: gameBridge.moveGraveyardOrderCard(modelData.id, 1)
                    }
                }
            }
            Button {
                visible: gameState.graveyardOrderPlayer === gameState.perspective.id
                text: "Confirm order"
                Layout.fillWidth: true
                onClicked: gameBridge.confirmGraveyardOrder()
            }
            Button {
                visible: gameState.graveyardOrderPlayer !== gameState.perspective.id
                text: "Switch perspective"
                Layout.fillWidth: true
                onClicked: gameBridge.switchPerspective()
            }
        }
    }

    Dialog {
        id: xPicker
        anchors.centerIn: parent
        implicitWidth: 360
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.choosingX
        title: (gameState.xIsAbility ? "Choose damage for " : "Choose X for ") + gameState.xCardName

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: "Affordable range: " + gameState.xMinimum + "\u2013" + gameState.xMaximum
                color: "#ffffff"
            }
            RowLayout {
                Button {
                    text: "\u2212"
                    enabled: gameState.xValue > gameState.xMinimum
                    onClicked: gameBridge.adjustX(-1)
                }
                Label {
                    text: (gameState.xIsAbility ? "Damage = " : "X = ") + gameState.xValue
                    color: "#ffd978"
                    font.bold: true
                    font.pixelSize: 22
                    horizontalAlignment: Text.AlignHCenter
                    Layout.preferredWidth: 100
                }
                Button {
                    text: "+"
                    enabled: gameState.xValue < gameState.xMaximum
                    onClicked: gameBridge.adjustX(1)
                }
            }
            RowLayout {
                Button {
                    text: "Cancel"
                    onClicked: gameBridge.cancelXCast()
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: gameState.xIsAbility ? "Activate" : "Cast"
                    onClicked: gameBridge.confirmXCast()
                }
            }
        }
    }

    Dialog {
        id: channelPicker
        anchors.centerIn: parent
        implicitWidth: 360
        modal: true
        title: "Channel life into mana"
        onOpened: channelAmount.value = 1

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: "Pay life to add colorless mana (maximum "
                      + gameState.channelMaximum + ")."
                color: "#ffffff"
            }
            RowLayout {
                Button {
                    text: "\u2212"
                    enabled: channelAmount.value > 1
                    onClicked: channelAmount.value--
                }
                SpinBox {
                    id: channelAmount
                    from: 1
                    to: Math.max(1, gameState.channelMaximum)
                    value: 1
                    editable: true
                }
                Button {
                    text: "+"
                    enabled: channelAmount.value < gameState.channelMaximum
                    onClicked: channelAmount.value++
                }
            }
            Label {
                text: "Life after payment: "
                      + (gameState.perspective.life - channelAmount.value)
                color: "#ffd978"
            }
            RowLayout {
                Button { text: "Cancel"; onClicked: channelPicker.close() }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Convert"
                    enabled: gameState.canChannel
                    onClicked: {
                        gameBridge.channelMana(channelAmount.value)
                        channelPicker.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: demonicAttorneyPicker
        anchors.centerIn: parent
        implicitWidth: 430
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.demonicAttorneyChoice
        title: "Demonic Attorney"

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: gameState.canChooseDemonicAttorney
                      ? "Concede the game, or have each player ante the unseen top card of their library."
                      : "Waiting for " + gameState.demonicAttorneyOpponent
                        + " to answer Demonic Attorney."
                color: "#ffffff"
            }
            RowLayout {
                visible: gameState.canChooseDemonicAttorney
                Layout.alignment: Qt.AlignRight
                Button {
                    text: "Add to ante"
                    onClicked: gameBridge.chooseDemonicAttorney(false)
                }
                Button {
                    text: "Concede"
                    onClicked: gameBridge.chooseDemonicAttorney(true)
                }
            }
            Button {
                visible: !gameState.canChooseDemonicAttorney
                text: "Switch to " + gameState.demonicAttorneyOpponent
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.switchPerspective()
            }
        }
    }

    Dialog {
        id: naturalSelectionPicker
        anchors.centerIn: parent
        width: Math.min(650, window.width - 48)
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.naturalSelectionChoice
        title: "Natural Selection — " + gameState.naturalSelectionTarget

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#ffffff"
                text: gameState.canChooseNaturalSelection
                      ? "Cards are shown top to bottom. Adjust the order, keep it as shown, or shuffle the entire library."
                      : "Waiting for " + gameState.naturalSelectionChooser
                        + " to inspect the library."
            }
            Repeater {
                model: gameState.canChooseNaturalSelection
                       ? gameState.naturalSelectionCards : []
                delegate: Frame {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    background: Rectangle {
                        color: "#202832"
                        border.color: "#536171"
                        radius: 7
                    }
                    RowLayout {
                        anchors.fill: parent
                        Label {
                            text: (index + 1) + (index === 0 ? " · TOP" : "")
                            color: index === 0 ? "#ffd978" : "#aeb8c3"
                            font.bold: true
                            Layout.preferredWidth: 58
                        }
                        CardItem {
                            cardData: modelData
                            interactive: false
                            onInspected: function(cardData) {
                                window.inspectedCard = cardData
                            }
                        }
                        Label {
                            text: modelData.name
                            color: "#ffffff"
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        Button {
                            text: "↑"
                            enabled: index > 0
                            onClicked: gameBridge.moveNaturalSelectionCard(
                                modelData.id, -1
                            )
                        }
                        Button {
                            text: "↓"
                            enabled: index + 1 < gameState.naturalSelectionCards.length
                            onClicked: gameBridge.moveNaturalSelectionCard(
                                modelData.id, 1
                            )
                        }
                    }
                }
            }
            Label {
                visible: gameState.canChooseNaturalSelection
                         && gameState.naturalSelectionCards.length === 0
                text: "That library is empty."
                color: "#ffd978"
            }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    visible: !gameState.canChooseNaturalSelection
                    text: "Switch to " + gameState.naturalSelectionChooser
                    onClicked: gameBridge.switchPerspective()
                }
                Item { Layout.fillWidth: true }
                Button {
                    visible: gameState.canChooseNaturalSelection
                    text: "Shuffle library"
                    onClicked: gameBridge.chooseNaturalSelection(true)
                }
                Button {
                    visible: gameState.canChooseNaturalSelection
                    text: "Use this order"
                    onClicked: gameBridge.chooseNaturalSelection(false)
                }
            }
        }
    }

    Dialog {
        id: librarySearchPicker
        anchors.centerIn: parent
        width: Math.min(900, window.width - 48)
        height: Math.min(690, window.height - 48)
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.librarySearchPending
        title: gameState.librarySearchSource + " — search library"
        onOpened: {
            librarySearchField.text = ""
            librarySearchField.forceActiveFocus()
        }

        contentItem: ColumnLayout {
            spacing: 10
            Label {
                visible: !gameState.canSearchLibrary
                text: gameState.librarySearchChooser
                      + " is searching their library privately."
                color: "#ffd978"
                Layout.fillWidth: true
            }
            Button {
                visible: !gameState.canSearchLibrary
                text: "Switch to " + gameState.librarySearchChooser
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.switchPerspective()
            }
            TextField {
                id: librarySearchField
                visible: gameState.canSearchLibrary
                Layout.fillWidth: true
                placeholderText: "Filter card names…"
                onTextChanged: gameBridge.setLibrarySearchFilter(text)
                Keys.onReturnPressed: {
                    if (gameState.librarySearchSelectedId)
                        gameBridge.confirmLibrarySearch()
                }
            }
            Label {
                visible: gameState.canSearchLibrary
                text: gameState.librarySearchShown + " of "
                      + gameState.librarySearchTotal + " cards shown"
                color: "#bfc7d1"
            }
            ScrollView {
                visible: gameState.canSearchLibrary
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                Flow {
                    width: librarySearchPicker.availableWidth - 24
                    spacing: 9
                    Repeater {
                        model: gameState.librarySearchCards
                        delegate: Rectangle {
                            required property var modelData
                            width: 116
                            height: 76
                            radius: 8
                            color: "transparent"
                            border.width: gameState.librarySearchSelectedId
                                          === modelData.id ? 4 : 0
                            border.color: "#ffd54a"
                            CardItem {
                                anchors.centerIn: parent
                                cardData: modelData
                                interactive: false
                                selectionOnly: true
                                onSelected: function(cardId) {
                                    gameBridge.selectLibrarySearchCard(cardId)
                                }
                                onInspected: function(cardData) {
                                    window.inspectedCard = cardData
                                }
                            }
                        }
                    }
                }
            }
            Label {
                visible: gameState.canSearchLibrary
                         && gameState.librarySearchShown === 0
                text: "No cards match this filter."
                color: "#ffd978"
            }
            RowLayout {
                visible: gameState.canSearchLibrary
                Layout.fillWidth: true
                Label {
                    text: gameState.librarySearchSelectedId
                          ? "One card selected" : "Select one card"
                    color: gameState.librarySearchSelectedId
                           ? "#ffd978" : "#bfc7d1"
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Choose card"
                    enabled: !!gameState.librarySearchSelectedId
                    onClicked: gameBridge.confirmLibrarySearch()
                }
            }
        }
    }

    Dialog {
        id: landTypePicker
        anchors.centerIn: parent
        implicitWidth: 360
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.choosingLandType
        title: "Choose a land type for " + gameState.landTypeCardName

        contentItem: ColumnLayout {
            spacing: 8
            Repeater {
                model: gameState.landTypeChoices
                Button {
                    required property string modelData
                    text: modelData
                    Layout.fillWidth: true
                    onClicked: gameBridge.chooseLandType(modelData)
                }
            }
            Button {
                text: "Cancel"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.cancelLandTypeChoice()
            }
        }
    }

    Dialog {
        id: modePicker
        anchors.centerIn: parent
        implicitWidth: 360
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.choosingMode
        title: "Choose how to cast " + gameState.modeCardName

        contentItem: ColumnLayout {
            spacing: 8
            Repeater {
                model: gameState.modeChoices
                Button {
                    required property string modelData
                    text: modelData
                    Layout.fillWidth: true
                    onClicked: gameBridge.chooseCastingMode(modelData)
                }
            }
            Button {
                text: "Cancel"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.cancelCastingMode()
            }
        }
    }

    Dialog {
        id: damageSourcePicker
        anchors.centerIn: parent
        implicitWidth: 400
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.choosingDamageSource
        title: "Choose a source for " + gameState.damageSourceCardName

        contentItem: ColumnLayout {
            spacing: 8
            Repeater {
                model: gameState.damageSourceChoices
                Button {
                    required property var modelData
                    text: modelData.label
                    Layout.fillWidth: true
                    onClicked: gameBridge.chooseDamageSource(modelData.key)
                }
            }
            Button {
                text: "Cancel"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.cancelDamageSourceChoice()
            }
        }
    }

    Dialog {
        id: redirectionAmountPicker
        anchors.centerIn: parent
        implicitWidth: 360
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.choosingRedirectionAmount
        title: "Choose damage to redirect"

        contentItem: ColumnLayout {
            spacing: 12
            RowLayout {
                Button {
                    text: "\u2212"
                    enabled: gameState.redirectionAmount > 1
                    onClicked: gameBridge.adjustRedirectionAmount(-1)
                }
                Label {
                    text: gameState.redirectionAmount
                    color: "#ffd978"
                    font.bold: true
                    font.pixelSize: 22
                    horizontalAlignment: Text.AlignHCenter
                    Layout.preferredWidth: 100
                }
                Button {
                    text: "+"
                    enabled: gameState.redirectionAmount
                             < gameState.redirectionMaximum
                    onClicked: gameBridge.adjustRedirectionAmount(1)
                }
            }
            RowLayout {
                Button {
                    text: "Back"
                    onClicked: gameBridge.cancelRedirectionAmount()
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Redirect"
                    onClicked: gameBridge.confirmRedirectionAmount()
                }
            }
        }
    }

    Dialog {
        id: combatDamagePicker
        anchors.centerIn: parent
        width: Math.min(620, window.width - 48)
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.choosingCombatDamage
        title: "Assign combat damage"

        contentItem: ScrollView {
            implicitHeight: Math.min(damageAssignmentColumn.implicitHeight,
                                     window.height * 0.65)
            clip: true

            ColumnLayout {
                id: damageAssignmentColumn
                width: combatDamagePicker.availableWidth
                spacing: 14

                Label {
                    text: "Divide each creature's full power among its combat opponents."
                    color: "#ffffff"
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Label {
                    visible: !gameState.combatDamageCanAssign
                    text: "Waiting for " + gameState.combatDamageWaitingFor
                          + " to assign combat damage."
                    color: "#ffd978"
                    Layout.fillWidth: true
                }
                Button {
                    visible: !gameState.combatDamageCanAssign
                    text: "Switch to " + gameState.combatDamageWaitingFor
                    Layout.alignment: Qt.AlignRight
                    onClicked: gameBridge.switchPerspective()
                }

                Repeater {
                    model: gameState.combatDamageAssignments
                    delegate: Frame {
                        id: assignmentGroup
                        required property var modelData
                        property string damageSourceId: modelData.sourceId
                        Layout.fillWidth: true
                        background: Rectangle {
                            color: "#202832"
                            border.color: assignmentGroup.modelData.valid
                                          ? "#536171" : "#d39155"
                            radius: 7
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            Label {
                                id: damageSourceLabel
                                text: assignmentGroup.modelData.sourceName
                                      + " assigns "
                                      + assignmentGroup.modelData.assigned
                                      + " of " + assignmentGroup.modelData.power
                                color: assignmentGroup.modelData.valid
                                       ? "#ffffff" : "#ffd978"
                                font.bold: true
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    acceptedButtons: Qt.NoButton
                                    onEntered: window.inspectedCard =
                                               assignmentGroup.modelData.sourceCard
                                }
                            }
                            Repeater {
                                model: assignmentGroup.modelData.recipients
                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Label {
                                        id: damageRecipientLabel
                                        text: modelData.name
                                        color: "#dce3ea"
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            acceptedButtons: Qt.NoButton
                                            onEntered: window.inspectedCard =
                                                       modelData.cardData
                                        }
                                    }
                                    Button {
                                        text: "\u2212"
                                        enabled: modelData.amount > 0
                                        Layout.preferredWidth: 42
                                        onClicked: gameBridge.adjustCombatDamage(
                                            assignmentGroup.damageSourceId,
                                            modelData.id, -1)
                                    }
                                    Label {
                                        text: modelData.amount
                                        color: "#ffd978"
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        Layout.preferredWidth: 36
                                    }
                                    Button {
                                        text: "+"
                                        enabled: assignmentGroup.modelData.assigned
                                                 < assignmentGroup.modelData.power
                                        Layout.preferredWidth: 42
                                        onClicked: gameBridge.adjustCombatDamage(
                                            assignmentGroup.damageSourceId,
                                            modelData.id, 1)
                                    }
                                }
                            }
                        }
                    }
                }

                Button {
                    text: "Confirm assignments"
                    enabled: gameState.combatDamageValid
                    Layout.alignment: Qt.AlignRight
                    onClicked: gameBridge.confirmCombatDamage()
                }
            }
        }
    }

    Connections {
        target: gameBridge
        function onStateChanged() { window.gameState = gameBridge.state }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        ColumnLayout {
            Layout.preferredWidth: 170
            Layout.minimumWidth: 150
            Layout.fillHeight: true
            spacing: 12

            PlayerStatus {
                Layout.fillWidth: true
                Layout.fillHeight: true
                playerData: gameState.opponent
                ownView: false
                onTargeted: function(playerId) { gameBridge.targetPlayer(playerId) }
            }
            PlayerStatus {
                Layout.fillWidth: true
                Layout.fillHeight: true
                playerData: gameState.perspective
                ownView: true
                onTargeted: function(playerId) { gameBridge.targetPlayer(playerId) }
            }
        }

        ScrollView {
            id: gameScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                width: gameScroll.availableWidth
                // Fill the viewport when there is spare room, but retain the
                // natural content height (and therefore scrolling) in a short
                // window or when contextual controls make the command bar tall.
                height: Math.max(implicitHeight, gameScroll.availableHeight)
                spacing: 9

                ZonePanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 190
                    Layout.preferredHeight: 200
                    playerData: gameState.opponent
                    interactive: gameState.settingBlockers || gameState.upkeepLandChoiceRequired
                                 || gameState.canChooseLich || gameState.canChooseKudzu
                                 || gameState.canChooseClone
                                 || gameState.canChooseDoppelganger
                    selectionOnly: gameState.settingBlockers || gameState.upkeepLandChoiceRequired
                                   || gameState.canChooseLich || gameState.canChooseKudzu
                                   || gameState.canChooseClone
                                   || gameState.canChooseDoppelganger
                    targeting: gameState.targeting
                    frontAtBottom: true
                    onSelected: function(cardId) { gameBridge.toggleCard(cardId) }
                    onInspected: function(cardData) { window.inspectedCard = cardData }
                }

                Frame {
                    Layout.fillWidth: true
                    background: Rectangle {
                        color: "#29313b"
                        border.color: "#536171"
                        radius: 9
                    }
                    ColumnLayout {
                        anchors.fill: parent
                        RowLayout {
                            Label {
                                text: "Turn " + gameState.turn + " · " + gameState.phase
                                      + " · Active: " + gameState.activePlayer
                                      + (gameState.combatStep
                                         ? " · Combat: " + gameState.combatStep : "")
                                color: "#ffffff"
                                font.bold: true
                                font.pixelSize: 17
                            }
                            Item { Layout.fillWidth: true }
                            Button {
                                visible: gameState.canAdvance
                                text: gameState.advanceLabel
                                onClicked: gameBridge.advance()
                            }
                            Button {
                                visible: gameState.canDiscard
                                text: gameState.effectDiscardRequired
                                      ? "Discard " + gameState.effectDiscardCount
                                        + " for " + gameState.effectDiscardPlayer
                                      : "Discard selected"
                                onClicked: gameBridge.discardSelected()
                            }
                            Button {
                                visible: gameState.canChooseBalance
                                text: "Choose " + gameState.balanceCount + " "
                                      + gameState.balanceCategory
                                      + (gameState.balanceCount === 1 ? "" : "s")
                                onClicked: gameBridge.chooseBalanceSelected()
                            }
                            Button {
                                visible: gameState.canChooseLich
                                text: "Destroy " + gameState.lichChoiceCount
                                      + " for Lich"
                                onClicked: gameBridge.chooseLichSelected()
                            }
                            Label {
                                visible: gameState.lichChoiceRequired
                                         && !gameState.canChooseLich
                                text: gameState.lichChoicePlayer
                                      + " chooses cards for Lich"
                                color: "#ffd978"
                            }
                            Button {
                                visible: gameState.canChooseUntap
                                text: "Untap " + gameState.untapChoiceCount + " "
                                      + gameState.untapChoiceType
                                      + (gameState.untapChoiceCount === 1 ? "" : "s")
                                onClicked: gameBridge.chooseUntapSelected()
                            }
                            Button {
                                visible: gameState.canChooseUpkeepLand
                                text: "Choose land"
                                onClicked: gameBridge.chooseUpkeepLand()
                            }
                            Button {
                                visible: gameState.canChannel
                                text: "Channel mana"
                                onClicked: channelPicker.open()
                            }
                            Label {
                                visible: gameState.upkeepLandChoiceRequired
                                text: gameState.upkeepLandChoicePlayer
                                      + " chooses a land for "
                                      + gameState.upkeepLandChoiceSource
                                color: "#ffd978"
                            }
                            Label {
                                visible: gameState.kudzuChoiceRequired
                                text: gameState.canChooseKudzu
                                      ? "Choose a land for Kudzu"
                                      : gameState.kudzuChoicePlayer
                                        + " chooses a land for Kudzu"
                                color: "#ffd978"
                            }
                            Label {
                                visible: gameState.cloneChoiceRequired
                                text: gameState.canChooseClone
                                      ? "Choose a creature for "
                                        + gameState.creatureCopyChoiceSource
                                      : gameState.cloneChoicePlayer
                                        + " chooses a creature for "
                                        + gameState.creatureCopyChoiceSource
                                color: "#ffd978"
                            }
                            Button {
                                visible: gameState.canChooseDoppelganger
                                text: "Keep current form"
                                onClicked: gameBridge.keepDoppelgangerForm()
                            }
                            Label {
                                visible: gameState.doppelgangerChoiceRequired
                                text: gameState.canChooseDoppelganger
                                      ? "Choose a different creature, or keep current form"
                                      : gameState.doppelgangerChoicePlayer
                                        + " chooses a Doppelganger form"
                                color: "#ffd978"
                            }
                            Label {
                                visible: gameState.untapChoiceRequired
                                text: "Choose permanents to untap ("
                                      + gameState.untapChoiceType + " limit)"
                                color: "#ffd978"
                            }
                            Label {
                                visible: gameState.balanceRequired
                                text: gameState.balanceProgress + ": "
                                      + gameState.balancePlayer + " chooses "
                                      + gameState.balanceCount + " "
                                      + gameState.balanceCategory
                                      + (gameState.balanceCount === 1 ? "" : "s")
                                color: "#ffd978"
                            }
                            Button {
                                text: "Switch perspective"
                                onClicked: gameBridge.switchPerspective()
                            }
                            Button { text: "New game"; onClicked: gameBridge.newGame() }
                        }
                        RowLayout {
                            visible: gameState.contextActionsVisible
                            Button {
                                visible: gameState.canBeginAttack
                                text: "Begin attack"
                                onClicked: gameBridge.beginCombat()
                            }
                            Button {
                                visible: gameState.canDeclareAttackers
                                enabled: gameState.canSetAttackingBand
                                text: gameState.attackingBandActionLabel
                                onClicked: gameBridge.setAttackingBand()
                            }
                            Button {
                                visible: gameState.canDeclareAttackers
                                text: "Declare attackers"
                                onClicked: gameBridge.declareAttackers()
                            }
                            Button {
                                visible: gameState.canDeclareBlockers
                                enabled: gameState.canSetBlocks
                                text: gameState.blockAssignmentLabel
                                onClicked: gameBridge.setBlocks()
                            }
                            Button {
                                visible: gameState.canDeclareBlockers
                                text: "Declare blockers"
                                onClicked: gameBridge.declareBlockers()
                            }
                            Button {
                                visible: gameState.targeting
                                text: "Cancel target"
                                onClicked: gameBridge.cancelTarget()
                            }
                            Button {
                                visible: gameState.upkeepPaymentRequired
                                         && gameState.upkeepPaymentPlayer
                                            === gameState.perspective.id
                                enabled: gameState.canPayUpkeep
                                text: gameState.upkeepCounterRedemption
                                      ? "Trade counter" : "Pay upkeep"
                                onClicked: gameBridge.chooseUpkeepPayment(true)
                            }
                            Button {
                                visible: gameState.upkeepPaymentRequired
                                         && gameState.upkeepPaymentPlayer
                                            === gameState.perspective.id
                                text: gameState.upkeepCounterRedemption
                                      ? "Keep counter" : "Decline upkeep"
                                onClicked: gameBridge.chooseUpkeepPayment(false)
                            }
                            Button {
                                visible: gameState.upkeepSacrificeRequired
                                         && gameState.upkeepSacrificePlayer
                                            === gameState.perspective.id
                                text: "Sacrifice selected"
                                onClicked: gameBridge.chooseUpkeepSacrifice()
                            }
                            Button {
                                visible: gameState.priorityRequired
                                enabled: gameState.hasPriority
                                text: "Pass priority"
                                onClicked: gameBridge.passPriority()
                            }
                            Button {
                                visible: gameState.priorityRequired
                                enabled: gameState.hasPriority
                                         && !gameState.autoPassingTurn
                                text: "Auto-pass turn"
                                onClicked: gameBridge.autoPassTurn()
                            }
                            Label {
                                visible: gameState.priorityRequired
                                text: "Priority: " + gameState.priorityPlayer
                                color: "#cbd2da"
                                font.bold: true
                            }
                            Item { Layout.fillWidth: true }
                        }
                        RowLayout {
                            visible: gameState.canChooseFireball
                            Layout.fillWidth: true
                            spacing: 7
                            Label {
                                text: "Fireball X=" + gameState.fireballX
                                      + (gameState.fireballTargetCount
                                         ? " · " + gameState.fireballDamageEach
                                           + " each" : " · choose targets")
                                color: "#ffd978"
                                font.bold: true
                            }
                            Button {
                                text: "−"
                                enabled: gameState.fireballX > 0
                                onClicked: gameBridge.adjustFireballX(-1)
                            }
                            Button {
                                text: "+"
                                enabled: gameState.fireballX
                                         < gameState.fireballXMaximum
                                onClicked: gameBridge.adjustFireballX(1)
                            }
                            ListView {
                                model: gameState.fireballTargets
                                orientation: ListView.Horizontal
                                spacing: 5
                                clip: true
                                Layout.fillWidth: true
                                Layout.preferredHeight: 38
                                delegate: Button {
                                    required property var modelData
                                    text: modelData.name + " ×"
                                    ToolTip.visible: hovered
                                    ToolTip.text: "Remove this target"
                                    onClicked: gameBridge.removeFireballTarget(
                                                   modelData.key)
                                }
                            }
                            Button {
                                text: "Cancel"
                                onClicked: gameBridge.cancelFireball()
                            }
                            Button {
                                text: "Cast Fireball"
                                enabled: gameState.fireballTargetCount > 0
                                onClicked: gameBridge.confirmFireball()
                            }
                        }
                        RowLayout {
                            visible: gameState.canChooseFork
                            Layout.fillWidth: true
                            spacing: 7
                            Label {
                                text: "Fork " + gameState.forkOriginalName
                                      + (gameState.forkOriginalName === "Fireball"
                                         ? " · X=" + gameState.forkX : "")
                                color: "#ffd978"
                                font.bold: true
                            }
                            ListView {
                                model: gameState.forkTargets
                                orientation: ListView.Horizontal
                                spacing: 5
                                clip: true
                                Layout.fillWidth: true
                                Layout.preferredHeight: 38
                                delegate: Button {
                                    required property var modelData
                                    text: modelData.name + " ×"
                                    ToolTip.visible: hovered
                                    ToolTip.text: "Remove this target"
                                    onClicked: gameBridge.removeForkTarget(
                                                   modelData.key)
                                }
                            }
                            Button {
                                text: "Cancel"
                                onClicked: gameBridge.cancelFork()
                            }
                            Button {
                                text: "Cast Fork"
                                enabled: gameState.forkTargetCount > 0
                                onClicked: gameBridge.confirmFork()
                            }
                        }
                        Label {
                            visible: !!gameState.message
                            text: gameState.message
                            color: "#ffd978"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Label {
                            visible: gameState.timedEvent
                            text: "Pending timed event: " + gameState.timedEvent
                            color: "#f2c66d"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        RowLayout {
                            visible: gameState.targeting
                                     && gameState.stackCards.length > 0
                            Label {
                                text: "Spells being cast:"
                                color: "#f2c66d"
                                font.bold: true
                            }
                            Repeater {
                                model: gameState.stackCards
                                Button {
                                    required property var modelData
                                    text: modelData.label
                                    enabled: modelData.legalTarget
                                    onClicked: gameBridge.toggleCard(modelData.id)
                                }
                            }
                        }
                        Label {
                            visible: gameState.damageWindow
                            text: gameState.damageWindow + " window — "
                                  + gameState.damagePackets.join("  +  ")
                            color: "#ef9f76"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        RowLayout {
                            visible: gameState.choosingPrevention
                            Label {
                                text: "Choose "
                                      + (gameState.preventingLifeLoss
                                         ? "life loss" : "damage")
                                      + " to prevent ("
                                      + gameState.preventionRemaining + " remaining):"
                                color: "#9fd6a8"
                                font.bold: true
                            }
                            Repeater {
                                model: gameState.damagePacketChoices
                                delegate: Button {
                                    required property var modelData
                                    text: modelData.label
                                    onClicked: gameBridge.chooseDamagePacket(modelData.id)
                                }
                            }
                            Button {
                                text: "Done"
                                visible: gameState.preventionPaid
                                         || gameState.preventingLifeLoss
                                onClicked: gameBridge.finishPrevention()
                            }
                            Button {
                                text: "Cancel"
                                visible: !gameState.preventionPaid
                                onClicked: gameBridge.cancelPrevention()
                            }
                        }
                        RowLayout {
                            visible: gameState.choosingRedirection
                            Label {
                                text: "Choose creature damage to redirect:"
                                color: "#9fd6a8"
                                font.bold: true
                            }
                            Repeater {
                                model: gameState.redirectionPacketChoices
                                delegate: Button {
                                    required property var modelData
                                    text: modelData.label
                                    onClicked: gameBridge.chooseRedirectionPacket(
                                                   modelData.id)
                                }
                            }
                            Button {
                                text: "Cancel"
                                onClicked: gameBridge.cancelRedirection()
                            }
                        }
                        Label {
                            visible: gameState.destructionWindow
                            text: "Regeneration window — destroy "
                                  + gameState.destructionTargets.join(", ")
                            color: "#ef9f76"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Label {
                            visible: gameState.stack.length > 0
                            text: "Current batch (declaration order): "
                                  + gameState.stack.join("  +  ")
                            color: "#f2c66d"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Label {
                            visible: gameState.rulesEvents.length > 0
                            text: "Catchable event"
                                  + (gameState.rulesEvents.length > 1 ? "s: " : ": ")
                                  + gameState.rulesEvents.join("  ·  ")
                            color: "#9fd6a8"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                ZonePanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 190
                    Layout.preferredHeight: 200
                    playerData: gameState.perspective
                    interactive: true
                    selectionOnly: gameState.settingBlockers || gameState.canChooseLich
                                   || gameState.canChooseKudzu || gameState.canChooseClone
                                   || gameState.canChooseDoppelganger
                    targeting: gameState.targeting
                    frontAtBottom: false
                    onSelected: function(cardId) { gameBridge.toggleCard(cardId) }
                    onActivated: function(cardId) { gameBridge.activateCard(cardId) }
                    onAbilityActivated: function(cardId, abilityIndex) {
                        gameBridge.activateAbility(cardId, abilityIndex)
                    }
                    onInspected: function(cardData) { window.inspectedCard = cardData }
                }
                HandPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 88
                    playerData: gameState.perspective
                    onSelected: function(cardId) { gameBridge.toggleCard(cardId) }
                    onActivated: function(cardId) { gameBridge.activateCard(cardId) }
                    onAbilityActivated: function(cardId, abilityIndex) {
                        gameBridge.activateAbility(cardId, abilityIndex)
                    }
                    onInspected: function(cardData) { window.inspectedCard = cardData }
                }
            }
        }

        CardPreview {
            Layout.preferredWidth: 320
            Layout.fillHeight: true
            cardData: window.inspectedCard
        }
    }
}
