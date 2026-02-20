// Register as frontend module for HACS
if (!customElements.get("netgear-sms-card")) {
  console.log("Registering netgear-sms-card");

  class NetgearSMSCard extends HTMLElement {
    setConfig(config) {
      this.config = config;
      this.hass = null;
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    getCardSize() {
        return 3;
    }

    _render() {
        if (!this._hass || !this.config) return;

        const root = this.shadowRoot || this.attachShadow({ mode: "open" });
        root.innerHTML = "";

        const card = document.createElement("ha-card");
        card.setAttribute("header", "SMS Inbox Manager");

        const style = document.createElement("style");
        style.textContent = `
      .content {
        padding: 16px;
      }
      .section {
        margin-bottom: 20px;
      }
      .section-title {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 12px;
        color: var(--primary-text-color);
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 12px;
        font-size: 13px;
      }
      th, td {
        text-align: left;
        padding: 8px 4px;
        border-bottom: 1px solid var(--divider-color);
      }
      th {
        font-weight: 600;
        background-color: var(--table-row-background-color, var(--secondary-background-color));
      }
      .sender {
        font-weight: 500;
        color: var(--primary-text-color);
      }
      .message {
        color: var(--secondary-text-color);
        word-break: break-word;
        max-width: 300px;
      }
      .timestamp {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .delete-btn {
        background: var(--error-color);
        color: white;
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        cursor: pointer;
      }
      .delete-btn:hover {
        opacity: 0.8;
      }
      .controls {
        display: grid;
        gap: 12px;
      }
      .control-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      }
      ha-textfield {
        width: 100%;
      }
      ha-checkbox {
        margin-right: 8px;
      }
      .checkbox-row {
        display: flex;
        align-items: center;
        padding: 8px 0;
      }
      .button-group {
        display: flex;
        gap: 8px;
        margin-top: 12px;
      }
      ha-button {
        flex: 1;
      }
      .status {
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 12px;
        font-size: 13px;
      }
      .status.loading {
        background-color: var(--secondary-background-color);
        color: var(--primary-text-color);
      }
      .status.success {
        background-color: var(--success-color, #4caf50);
        color: white;
      }
      .status.error {
        background-color: var(--error-color);
        color: white;
      }
      .no-messages {
        text-align: center;
        color: var(--secondary-text-color);
        padding: 20px;
      }
    `;

        const content = document.createElement("div");
        content.className = "content";

        // Status message
        if (this._statusMessage) {
            const status = document.createElement("div");
            status.className = `status ${this._statusClass}`;
            status.textContent = this._statusMessage;
            content.appendChild(status);
        }

        // Inbox section
        const inboxSection = document.createElement("div");
        inboxSection.className = "section";

        const inboxTitle = document.createElement("div");
        inboxTitle.className = "section-title";
        inboxTitle.textContent = "Inbox";
        inboxSection.appendChild(inboxTitle);

        // List/Refresh button
        const listButtonDiv = document.createElement("div");
        const listButton = document.createElement("ha-button");
        listButton.textContent = `${this._loading ? "Loading..." : "Refresh Inbox"}`;
        listButton.disabled = this._loading;
        listButton.onclick = () => this._fetchInbox();
        listButtonDiv.appendChild(listButton);
        inboxSection.appendChild(listButtonDiv);

        // Messages table
        if (this._messages && this._messages.length > 0) {
            const table = document.createElement("table");
            const thead = document.createElement("thead");
            const headerRow = document.createElement("tr");
            ["Sender", "Message", "Time", "Action"].forEach((h) => {
                const th = document.createElement("th");
                th.textContent = h;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement("tbody");
            this._messages.forEach((msg) => {
                const row = document.createElement("tr");
                const senderCell = document.createElement("td");
                senderCell.className = "sender";
                senderCell.textContent = msg.sender || "(unknown)";
                row.appendChild(senderCell);

                const msgCell = document.createElement("td");
                msgCell.className = "message";
                msgCell.textContent = msg.message || "(no content)";
                row.appendChild(msgCell);

                const timeCell = document.createElement("td");
                timeCell.className = "timestamp";
                timeCell.textContent = msg.timestamp ? this._formatTime(msg.timestamp) : "-";
                row.appendChild(timeCell);

                const actionCell = document.createElement("td");
                const deleteBtn = document.createElement("button");
                deleteBtn.className = "delete-btn";
                deleteBtn.textContent = "Delete";
                deleteBtn.onclick = () => this._deleteSMS([msg.id]);
                actionCell.appendChild(deleteBtn);
                row.appendChild(actionCell);

                tbody.appendChild(row);
            });
            table.appendChild(tbody);
            inboxSection.appendChild(table);
        } else if (this._messagesChecked) {
            const noMsg = document.createElement("div");
            noMsg.className = "no-messages";
            noMsg.textContent = "No messages in inbox";
            inboxSection.appendChild(noMsg);
        }

        content.appendChild(inboxSection);

        // Cleanup section
        const cleanupSection = document.createElement("div");
        cleanupSection.className = "section";

        const cleanupTitle = document.createElement("div");
        cleanupTitle.className = "section-title";
        cleanupTitle.textContent = "Cleanup Policy";
        cleanupSection.appendChild(cleanupTitle);

        const controls = document.createElement("div");
        controls.className = "controls";

        // Retain count
        const controlRow1 = document.createElement("div");
        controlRow1.className = "control-row";

        const retainInput = document.createElement("ha-textfield");
        retainInput.label = "Retain count";
        retainInput.type = "number";
        retainInput.value = this._retainCount || 24;
        retainInput.addEventListener("change", (e) => {
            this._retainCount = parseInt(e.target.value) || 24;
        });
        controlRow1.appendChild(retainInput);

        const retainDaysInput = document.createElement("ha-textfield");
        retainDaysInput.label = "Retain days";
        retainDaysInput.type = "number";
        retainDaysInput.value = this._retainDays || 0;
        retainDaysInput.addEventListener("change", (e) => {
            this._retainDays = parseInt(e.target.value) || 0;
        });
        controlRow1.appendChild(retainDaysInput);

        controls.appendChild(controlRow1);

        // Dry run and Execute buttons
        const dryRunRow = document.createElement("div");
        dryRunRow.className = "checkbox-row";

        const dryRunCheckbox = document.createElement("ha-checkbox");
        dryRunCheckbox.checked = this._dryRun !== false;
        dryRunCheckbox.addEventListener("change", (e) => {
            this._dryRun = e.target.checked;
        });
        dryRunRow.appendChild(dryRunCheckbox);

        const dryRunLabel = document.createElement("label");
        dryRunLabel.textContent = "Dry run (preview only, no deletion)";
        dryRunRow.appendChild(dryRunLabel);

        controls.appendChild(dryRunRow);

        const buttonGroup = document.createElement("div");
        buttonGroup.className = "button-group";

        const dryRunBtn = document.createElement("ha-button");
        dryRunBtn.textContent = "Preview";
        dryRunBtn.disabled = this._loading;
        dryRunBtn.onclick = () => this._runCleanup(true);
        buttonGroup.appendChild(dryRunBtn);

        const cleanupBtn = document.createElement("ha-button");
        cleanupBtn.classList.add("danger");
        cleanupBtn.textContent = "Delete";
        cleanupBtn.disabled = this._loading;
        cleanupBtn.onclick = () => {
            if (confirm("Delete messages according to policy? This cannot be undone.")) {
                this._runCleanup(false);
            }
        };
        buttonGroup.appendChild(cleanupBtn);

        controls.appendChild(buttonGroup);
        cleanupSection.appendChild(controls);
        content.appendChild(cleanupSection);

        card.appendChild(style);
        card.appendChild(content);
        root.appendChild(card);
    }

    _formatTime(timestamp) {
        try {
            const date = new Date(timestamp);
            return date.toLocaleString();
        } catch {
            return timestamp;
        }
    }

    async _fetchInbox() {
        this._loading = true;
        this._statusMessage = "Loading...";
        this._statusClass = "loading";
        this._render();

        try {
            await this._hass.callService("netgear_lte_sms_manager", "list_inbox", {
                host: this.config.host || undefined,
            });

            // Listen for event
            const listener = (event) => {
                if (event.detail.event_type === "netgear_lte_sms_manager_inbox_listed") {
                    this._messages = event.detail.event.data.messages || [];
                    this._messagesChecked = true;
                    this._statusMessage = `Loaded ${this._messages.length} message(s)`;
                    this._statusClass = "success";
                    this._hass.connection.removeEventListener("ha_events", listener);
                    this._render();
                }
            };
            this._hass.connection.addEventListener("ha_events", listener);

            setTimeout(() => {
                this._hass.connection.removeEventListener("ha_events", listener);
                this._loading = false;
                this._render();
            }, 5000);
        } catch (error) {
            this._statusMessage = `Error: ${error.message}`;
            this._statusClass = "error";
            this._loading = false;
            this._render();
        }
    }

    async _deleteSMS(ids) {
        if (!confirm(`Delete ${ids.length} message(s)?`)) return;

        this._loading = true;
        this._statusMessage = "Deleting...";
        this._statusClass = "loading";
        this._render();

        try {
            await this._hass.callService("netgear_lte_sms_manager", "delete_sms", {
                host: this.config.host || undefined,
                sms_id: ids,
            });

            this._statusMessage = `Deleted ${ids.length} message(s)`;
            this._statusClass = "success";
            this._loading = false;
            await this._fetchInbox();
        } catch (error) {
            this._statusMessage = `Error: ${error.message}`;
            this._statusClass = "error";
            this._loading = false;
            this._render();
        }
    }

    async _runCleanup(dryRun) {
        this._loading = true;
        this._statusMessage = dryRun ? "Previewing cleanup..." : "Running cleanup...";
        this._statusClass = "loading";
        this._render();

        try {
            await this._hass.callService("netgear_lte_sms_manager", "cleanup_inbox", {
                host: this.config.host || undefined,
                retain_count: this._retainCount || 24,
                retain_days: this._retainDays || 0,
                dry_run: dryRun,
            });

            // Listen for event
            const listener = (event) => {
                if (event.detail.event_type === "netgear_lte_sms_manager_cleanup_complete") {
                    const data = event.detail.event.data;
                    const count = data.count_deleted || 0;
                    this._statusMessage = `${dryRun ? "Preview" : "Cleanup"} complete: ${count} message(s) ${dryRun ? "would be" : ""} deleted`;
                    this._statusClass = "success";
                    this._hass.connection.removeEventListener("ha_events", listener);
                    this._loading = false;
                    this._render();
                }
            };
            this._hass.connection.addEventListener("ha_events", listener);

            setTimeout(() => {
                this._hass.connection.removeEventListener("ha_events", listener);
                this._loading = false;
                this._render();
            }, 5000);
        } catch (error) {
            this._statusMessage = `Error: ${error.message}`;
            this._statusClass = "error";
            this._loading = false;
            this._render();
        }
    }
  }

  customElements.define("netgear-sms-card", NetgearSMSCard);
}
